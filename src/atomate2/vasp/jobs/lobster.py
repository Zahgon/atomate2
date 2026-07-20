
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from jobflow import Flow, Response, job
from pymatgen.io.lobster import Lobsterin

from atomate2.lobster.jobs import LobsterMaker
from atomate2.vasp.jobs.base import BaseVaspMaker
from atomate2.vasp.powerups import update_user_incar_settings
from atomate2.vasp.sets.core import LobsterTightStaticSetGenerator

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core import Structure

    from atomate2.vasp.sets.base import VaspInputGenerator


logger = logging.getLogger(__name__)


@dataclass
class LobsterStaticMaker(BaseVaspMaker):

    name: str = "static_run"
    input_set_generator: VaspInputGenerator = field(
        default_factory=LobsterTightStaticSetGenerator
    )


@job
def get_basis_infos(
    structure: Structure,
    vasp_maker: BaseVaspMaker,
    address_max_basis: str = None,
    address_min_basis: str = None,
) -> dict:
    """
    Compute all relevant basis sets and maximum number of bands.

    Parameters
    ----------
    structure : .Structure
     A structure object.
    vasp_maker : .BaseVaspMaker
        Maker for Vasp job including a POTCAR.
    address_max_basis : str
        string to yaml file including basis set information.
    address_min_basis : str
        string to yaml file including basis set information.

    Returns
    -------
    dict
        Dictionary including number of bands and basis set information.
    """
    try:
        vis = vasp_maker.static_maker.input_set_generator
    except AttributeError:
        vis = vasp_maker.input_set_generator

    vis.structure = structure
    potcar_symbols = vis.potcar_symbols

    list_basis_dict = Lobsterin.get_all_possible_basis_functions(
        structure=structure,
        potcar_symbols=potcar_symbols,
        address_basis_file_max=address_max_basis,
        address_basis_file_min=address_min_basis,
    )

    n_band_list: list[int] = []
    for dict_for_basis in list_basis_dict:
        basis = [f"{key} {value}" for key, value in dict_for_basis.items()]
        lobsterin = Lobsterin(settingsdict={"basisfunctions": basis})
        n_bands = lobsterin._get_nbands(structure=structure)  # noqa: SLF001
        n_band_list.append(n_bands)

    return {"nbands": max(n_band_list), "basis_dict": list_basis_dict}


@job
def update_user_incar_settings_maker(
    vasp_maker: BaseVaspMaker,
    nbands: int,
    structure: Structure,
    prev_dir: Path | str,
) -> Response:
    """
    Update the INCAR settings of a maker.

    Parameters
    ----------
    vasp_maker : .BaseVaspMaker
        A maker for the static run with all parameters
        relevant for Lobster.
    nbands : int
        integer indicating the correct number of bands
    structure : .Structure
        Structure object.
    prev_dir : Path or str
        Path or string to vasp files.

    Returns
    -------
    .BaseVaspMaker
        LobsterStaticMaker with correct number of bands.
    """
    vasp_maker = update_user_incar_settings(vasp_maker, {"NBANDS": nbands})
    vasp_job = vasp_maker.make(structure=structure, prev_dir=prev_dir)
    return Response(replace=vasp_job)


@job
def get_lobster_jobs(
    lobster_maker: LobsterMaker | None,
    basis_dict: dict,
    optimization_dir: Path | str,
    optimization_uuid: str,
    static_dir: Path | str,
    static_uuid: str,
) -> Response:
    """
    Create a list of Lobster jobs with different basis sets.

    Parameters
    ----------
    lobster_maker : .LobsterMaker or None
        maker for the Lobster jobs
    basis_dict : dict
        dict including basis set information.
    optimization_dir : Path or str
        Path to optimization run.
    optimization_uuid : str
        uuid of optimization run.
    static_dir : Path or str
        Path to static VASP calculation containing the WAVECAR.
    static_uuid : str
        Uuid of static run.

    Returns
    -------
    list
        List of Lobster jobs.
    """
    jobs = []
    outputs: dict[str, Any] = {
        "optimization_dir": optimization_dir,
        "optimization_uuid": optimization_uuid,
        "static_dir": static_dir,
        "static_uuid": static_uuid,
        "lobster_uuids": [],
        "lobster_dirs": [],
        "lobster_task_documents": [],
    }

    lobster_maker = lobster_maker or LobsterMaker()

    for idx, basis in enumerate(basis_dict):
        lobster_job = lobster_maker.make(wavefunction_dir=static_dir, basis_dict=basis)
        lobster_job.append_name(f"_run_{idx}")
        outputs["lobster_uuids"].append(lobster_job.output.uuid)
        outputs["lobster_dirs"].append(lobster_job.output.dir_name)
        outputs["lobster_task_documents"].append(lobster_job.output)
        jobs.append(lobster_job)

    flow = Flow(jobs, output=outputs)
    return Response(replace=flow)
