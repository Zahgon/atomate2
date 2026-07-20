
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Flow, Maker, OnMissing

from atomate2.vasp.flows.core import (
    DoubleRelaxMaker,
    HSEUniformBandStructureMaker,
    UniformBandStructureMaker,
)
from atomate2.vasp.jobs.core import (
    HSEBSMaker,
    HSEStaticMaker,
    NonSCFMaker,
    StaticMaker,
    TightRelaxMaker,
)
from atomate2.vasp.jobs.elph import (
    DEFAULT_ELPH_TEMPERATURES,
    DEFAULT_MIN_SUPERCELL_LENGTH,
    SupercellElectronPhononDisplacedStructureMaker,
    calculate_electron_phonon_renormalisation,
    run_elph_displacements,
)
from atomate2.vasp.sets.core import (
    HSEBSSetGenerator,
    HSEStaticSetGenerator,
    NonSCFSetGenerator,
    StaticSetGenerator,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core import Structure

    from atomate2.vasp.jobs.base import BaseVaspMaker


@dataclass
class ElectronPhononMaker(Maker):

    name: str = "electron phonon"
    temperatures: tuple[float, ...] = DEFAULT_ELPH_TEMPERATURES
    min_supercell_length: float = DEFAULT_MIN_SUPERCELL_LENGTH
    relax_maker: BaseVaspMaker | None = field(
        default_factory=lambda: DoubleRelaxMaker.from_relax_maker(TightRelaxMaker())
    )
    static_maker: BaseVaspMaker = field(default_factory=StaticMaker)
    elph_displacement_maker: SupercellElectronPhononDisplacedStructureMaker = field(
        default_factory=SupercellElectronPhononDisplacedStructureMaker
    )
    uniform_maker: BaseVaspMaker = field(
        default_factory=lambda: UniformBandStructureMaker(
            static_maker=StaticMaker(
                input_set_generator=StaticSetGenerator(
                    auto_ispin=True,
                    user_incar_settings={"KSPACING": None, "EDIFF": 1e-5},
                    user_kpoints_settings={"reciprocal_density": 50},
                ),
            ),
            bs_maker=NonSCFMaker(
                input_set_generator=NonSCFSetGenerator(
                    reciprocal_density=100,  # dense BS mesh
                    user_incar_settings={"LORBIT": 10},  # disable site projections
                ),
                task_document_kwargs={
                    "strip_bandstructure_projections": False,
                    "strip_dos_projections": False,
                },
            ),
        )
    )

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Create a electron-phonon coupling workflow.

        Parameters
        ----------
        structure: .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            An electron phonon coupling workflow.
        """
        jobs = []

        if self.relax_maker is not None:
            relax = self.relax_maker.make(structure, prev_dir=prev_dir)
            jobs.append(relax)
            structure = relax.output.structure
            prev_dir = relax.output.dir_name

        static = self.static_maker.make(structure, prev_dir=prev_dir)

        elph_maker = deepcopy(self.elph_displacement_maker)
        elph_maker.temperatures = self.temperatures
        elph_maker.min_supercell_length = self.min_supercell_length
        elph = elph_maker.make(static.output.structure, prev_dir=static.output.dir_name)

        supercell_dos = self.uniform_maker.make(
            elph.output.structure, prev_dir=static.output.dir_name
        )
        supercell_dos.append_name(" bulk supercell")

        displaced_doses = run_elph_displacements(
            elph.output.calcs_reversed[0].output.elph_displaced_structures.temperatures,
            elph.output.calcs_reversed[0].output.elph_displaced_structures.structures,
            self.uniform_maker,
            prev_dir=static.output.dir_name,
            original_structure=static.output.structure,
            supercell_structure=elph.output.structure,
        )

        renorm = calculate_electron_phonon_renormalisation(
            displaced_doses.output["temperatures"],
            displaced_doses.output["band_structures"],
            displaced_doses.output["structures"],
            displaced_doses.output["uuids"],
            displaced_doses.output["dirs"],
            supercell_dos.output.vasp_objects["bandstructure"],
            supercell_dos.output.structure,
            supercell_dos.output.uuid,
            supercell_dos.output.dir_name,
            elph.output.uuid,
            elph.output.dir_name,
            static.output.structure,
        )

        renorm.config.on_missing_references = OnMissing.NONE

        jobs.extend([static, elph, supercell_dos, displaced_doses, renorm])
        return Flow(jobs, renorm.output, name=self.name)


@dataclass
class HSEElectronPhononMaker(ElectronPhononMaker):

    name: str = "hse electron phonon"
    uniform_maker: BaseVaspMaker = field(
        default_factory=lambda: HSEUniformBandStructureMaker(
            static_maker=HSEStaticMaker(
                input_set_generator=HSEStaticSetGenerator(
                    auto_ispin=True,
                    user_incar_settings={"KSPACING": None, "EDIFF": 1e-5},
                    user_kpoints_settings={"reciprocal_density": 64},
                )
            ),
            bs_maker=HSEBSMaker(
                input_set_generator=HSEBSSetGenerator(
                    user_incar_settings={"LORBIT": 10},  # disable site projections
                    user_kpoints_settings={"reciprocal_density": 200},  # dense BS mesh
                ),
                task_document_kwargs={
                    "strip_bandstructure_projections": True,
                    "strip_dos_projections": True,
                },
            ),
        )
    )
