
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from emmet.core.band_theory import ElectronicBS
from jobflow import Flow, Response, job

from atomate2 import SETTINGS
from atomate2.vasp.jobs.base import BaseVaspMaker, vasp_job
from atomate2.vasp.jobs.core import TransmuterMaker
from atomate2.vasp.schemas.elph import ElectronPhononRenormalisationDoc
from atomate2.vasp.sets.core import ElectronPhononSetGenerator

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core import Structure
    from pymatgen.electronic_structure.bandstructure import BandStructure

DEFAULT_ELPH_TEMPERATURES = (0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000)
DEFAULT_MIN_SUPERCELL_LENGTH = 15
logger = logging.getLogger(__name__)


@dataclass
class SupercellElectronPhononDisplacedStructureMaker(TransmuterMaker):

    name: str = "supercell electron phonon displacements"
    input_set_generator: ElectronPhononSetGenerator = field(
        default_factory=ElectronPhononSetGenerator
    )
    transformations: tuple[str, ...] = ("SupercellTransformation",)
    transformation_params: tuple[dict, ...] = None
    temperatures: tuple[float, ...] = DEFAULT_ELPH_TEMPERATURES
    min_supercell_length: float = DEFAULT_MIN_SUPERCELL_LENGTH

    @vasp_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> Response:
        """Run a transmuter VASP job.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.
        """
        dim = self.min_supercell_length / np.array(structure.lattice.abc)
        scaling_matrix = np.diag(np.ceil(dim).astype(int)).tolist()
        if self.transformation_params is None:
            self.transformation_params = ({"scaling_matrix": scaling_matrix},)

        self.input_set_generator.temperatures = self.temperatures

        return super().make.original(self, structure, prev_dir)


@job
def run_elph_displacements(
    temperatures: list[float],
    structures: list[Structure],
    vasp_maker: BaseVaspMaker,
    prev_dir: str | Path | None = None,
    original_structure: Structure = None,
    supercell_structure: Structure = None,
) -> Response:
    """
    Run electron phonon displaced structures.

    Note, this job will replace itself with N displacement calculations.

    Parameters
    ----------
    temperatures : list of float
        Temperatures at which electron phonon structures were generated.
    structures : list of Structure
        Electron phonon displaced structures for each temperature.
    vasp_maker : BaseVaspMaker
        A maker to generate VASP calculations on the displaced structures.
    prev_dir : str or Path or None
        A previous VASP directory to use for copying VASP outputs.
    original_structure : Structure
        The original structure before supercell is made and before electron phonon
        displacements.
    """
    if len(temperatures) != len(structures):
        raise ValueError(
            f"Number of temperatures ({len(temperatures)}) does not equal number of "
            f"structures ({len(structures)})."
        )

    jobs = []
    outputs: dict[str, list] = {
        "temperatures": [],
        "band_structures": [],
        "structures": [],
        "uuids": [],
        "dirs": [],
    }
    for temp, structure in zip(temperatures, structures, strict=True):
        elph_job = vasp_maker.make(structure, prev_dir=prev_dir)
        elph_job.append_name(f" T={temp}")

        info = {
            "temperature": temp,
            "original_structure": original_structure,
            "supercell_structure": supercell_structure,
        }
        elph_job.update_maker_kwargs(
            {"_set": {"write_additional_data->elph_info:json": info}}, dict_mod=True
        )

        jobs.append(elph_job)

        outputs["temperatures"].append(temp)
        outputs["band_structures"].append(elph_job.output.vasp_objects["bandstructure"])
        outputs["structures"].append(elph_job.output.structure)
        outputs["dirs"].append(elph_job.output.dir_name)
        outputs["uuids"].append(elph_job.output.uuid)

    disp_flow = Flow(jobs, outputs)
    return Response(replace=disp_flow)


@job(output_schema=ElectronPhononRenormalisationDoc)
def calculate_electron_phonon_renormalisation(
    temperatures: list[float],
    displacement_band_structures: list[BandStructure | ElectronicBS],
    displacement_structures: list[Structure],
    displacement_uuids: list[str],
    displacement_dirs: list[str],
    bulk_band_structure: BandStructure | ElectronicBS,
    bulk_structure: Structure,
    bulk_uuid: str,
    bulk_dir: str,
    elph_uuid: str,
    elph_dir: str,
    original_structure: Structure,
) -> ElectronPhononRenormalisationDoc:
    """
    Calculate the electron-phonon renormalisation of the band gap.

    Parameters
    ----------
    temperatures : list of float
        The temperatures at which electron phonon properties were calculated.
    displacement_band_structures :
        list of pymatgen .BandStructure or emmet.core .ElectronicBS
        The electron-phonon displaced band structures.
    displacement_structures : list of Structure
        The electron-phonon displaced structures.
    displacement_uuids : list of str
        The UUIDs of the electron-phonon displaced band structure calculations.
    displacement_dirs : list of str
        The calculation directories of the electron-phonon displaced band structure
        calculations.
    bulk_band_structure : pymatgen .BandStructure or emmet.core .ElectronicBS
        The band structure of the bulk undisplaced supercell calculation.
    bulk_structure : Structure
        The structure of the bulk undisplaced supercell.
    bulk_uuid : str
        The UUID of the bulk undisplaced supercell band structure calculation.
    bulk_dir : str
        The directory of the bulk undisplaced supercell band structure calculation.
    elph_uuid : str
        The UUID of electron-phonon calculation that generated the displaced structures.
    elph_dir : str
        The directory of electron-phonon calculation that generated the displaced
        structures.
    original_structure : Structure
        The original primitive structure for which electron-phonon calculations
        were performed.
    """
    if bulk_structure is None:
        raise ValueError(
            "Bulk (undisplaced) supercell band structure calculation failed. Cannot "
            "calculate electron-phonon renormalisation."
        )

    keep = [idx for idx, b in enumerate(displacement_band_structures) if b is not None]
    temperatures = [temperatures[i] for i in keep]

    if SETTINGS.VASP_USE_EMMET_MODELS:
        displacement_band_structures = [
            ElectronicBS(**displacement_band_structures[i]).to_pmg() for i in keep
        ]
        bulk_bs = ElectronicBS(**bulk_band_structure).to_pmg()
    else:
        displacement_band_structures = [displacement_band_structures[i] for i in keep]
        bulk_bs = bulk_band_structure

    displacement_structures = [displacement_structures[i] for i in keep]
    displacement_uuids = [displacement_uuids[i] for i in keep]
    displacement_dirs = [displacement_dirs[i] for i in keep]

    logger.info("Calculating electron-phonon renormalisation")

    return ElectronPhononRenormalisationDoc.from_band_structures(
        temperatures,
        displacement_band_structures,
        displacement_structures,
        displacement_uuids,
        displacement_dirs,
        bulk_bs,
        bulk_structure,
        bulk_uuid,
        bulk_dir,
        elph_uuid,
        elph_dir,
        original_structure,
    )
