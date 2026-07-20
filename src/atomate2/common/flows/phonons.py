
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Flow, Maker

from atomate2 import SETTINGS
from atomate2.common.jobs.phonons import (
    generate_frequencies_eigenvectors,
    generate_phonon_displacements,
    get_supercell_size,
    get_total_energy_per_cell,
    run_phonon_displacements,
)
from atomate2.common.jobs.utils import structure_to_conventional, structure_to_primitive

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    from emmet.core.math import Matrix3D
    from pymatgen.core.structure import Structure

    from atomate2.aims.jobs.base import BaseAimsMaker
    from atomate2.forcefields.jobs import ForceFieldRelaxMaker, ForceFieldStaticMaker
    from atomate2.torchsim.core import TorchSimOptimizeMaker, TorchSimStaticMaker
    from atomate2.vasp.jobs.base import BaseVaspMaker

SUPPORTED_CODES = frozenset(("vasp", "aims", "forcefields", "ase", "torchsim"))


@dataclass
class BasePhononMaker(Maker, ABC):

    name: str = "phonon"
    sym_reduce: bool = True
    symprec: float = SETTINGS.PHONON_SYMPREC
    displacement: float = 0.01
    min_length: float | None = 20.0
    max_length: float | None = None
    prefer_90_degrees: bool = True
    allow_orthorhombic: bool = False
    get_supercell_size_kwargs: dict = field(default_factory=dict)
    use_symmetrized_structure: Literal["primitive", "conventional"] | None = None
    bulk_relax_maker: (
        ForceFieldRelaxMaker
        | BaseVaspMaker
        | BaseAimsMaker
        | TorchSimOptimizeMaker
        | None
    ) = None
    static_energy_maker: (
        ForceFieldRelaxMaker
        | BaseVaspMaker
        | BaseAimsMaker
        | TorchSimStaticMaker
        | None
    ) = None
    born_maker: ForceFieldStaticMaker | BaseVaspMaker | TorchSimStaticMaker | None = (
        None
    )
    phonon_displacement_maker: (
        ForceFieldStaticMaker | BaseVaspMaker | BaseAimsMaker | TorchSimStaticMaker
    ) = None
    create_thermal_displacements: bool = True
    generate_frequencies_eigenvectors_kwargs: dict = field(
        default_factory=lambda: {
            "create_force_constants_file": False,
            "force_constants_filename": "FORCE_CONSTANTS",
            "calculate_pdos": False,
        }
    )

    kpath_scheme: str = "seekpath"
    code: str = None
    store_force_constants: bool = True
    socket: bool = False

    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
        born: list[Matrix3D] | None = None,
        epsilon_static: Matrix3D | None = None,
        total_dft_energy_per_formula_unit: float | None = None,
        supercell_matrix: Matrix3D | None = None,
    ) -> Flow:
        """Make flow to calculate the phonon properties.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object. Please start with a structure
            that is nearly fully optimized as the internal optimizers
            have very strict settings!
        prev_dir : str or Path or None
            A previous calculation directory to use for copying outputs.
        born: Matrix3D
            Instead of recomputing Born charges and epsilon, these values can also be
            provided manually. If born and epsilon_static are provided, the born run
            will be skipped it can be provided in the VASP convention with information
            for every atom in unit cell. Please be careful when converting structures
            within in this workflow as this could lead to errors
        epsilon_static: Matrix3D
            The high-frequency dielectric constant to use instead of recomputing born
            charges and epsilon. If born, epsilon_static are provided, the born run
            will be skipped
        total_dft_energy_per_formula_unit: float
            It has to be given per formula unit (as a result in corresponding Doc).
            Instead of recomputing the energy of the bulk structure every time, this
            value can also be provided in eV. If it is provided, the static run will be
            skipped. This energy is the typical output dft energy of the DFT workflow.
            No conversion needed.
        supercell_matrix: list
            Instead of min_length, also a supercell_matrix can be given, e.g.
            [[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]
        """
        use_symmetrized_structure = self.use_symmetrized_structure
        kpath_scheme = self.kpath_scheme
        valid_structs = (None, "primitive", "conventional")
        if use_symmetrized_structure not in valid_structs:
            raise ValueError(
                f"Invalid {use_symmetrized_structure=}, use one of {valid_structs}"
            )

        if use_symmetrized_structure != "primitive" and kpath_scheme != "seekpath":
            raise ValueError(
                f"You can't use {kpath_scheme=} with the primitive standard "
                "structure, please use seekpath"
            )

        valid_schemes = ("seekpath", "hinuma", "setyawan_curtarolo", "latimer_munro")
        if kpath_scheme not in valid_schemes:
            raise ValueError(
                f"{kpath_scheme=} is not implemented, use one of {valid_schemes}"
            )

        if self.code is None or self.code not in SUPPORTED_CODES:
            raise ValueError(
                "The code variable must be passed and it must be a supported code."
                f" Supported codes are: {SUPPORTED_CODES}"
            )

        jobs = []

        if self.use_symmetrized_structure == "primitive":
            prim_job = structure_to_primitive(structure, self.symprec)
            jobs.append(prim_job)
            structure = prim_job.output
        elif self.use_symmetrized_structure == "conventional":
            conv_job = structure_to_conventional(structure, self.symprec)
            jobs.append(conv_job)
            structure = conv_job.output

        optimization_run_job_dir = None
        optimization_run_uuid = None

        if self.bulk_relax_maker is not None:
            bulk_kwargs = {}
            if self.prev_calc_dir_argname is not None:
                bulk_kwargs[self.prev_calc_dir_argname] = prev_dir
            bulk = self.bulk_relax_maker.make(structure, **bulk_kwargs)
            jobs.append(bulk)
            structure = bulk.output.structure
            prev_dir = bulk.output.dir_name
            optimization_run_job_dir = bulk.output.dir_name
            optimization_run_uuid = bulk.output.uuid

        if supercell_matrix is None:
            supercell_job = get_supercell_size(
                structure=structure,
                min_length=self.min_length,
                max_length=self.max_length,
                prefer_90_degrees=self.prefer_90_degrees,
                allow_orthorhombic=self.allow_orthorhombic,
                **self.get_supercell_size_kwargs,
            )
            jobs.append(supercell_job)
            supercell_matrix = supercell_job.output

        total_dft_energy = None
        static_run_job_dir = None
        static_run_uuid = None
        if (self.static_energy_maker is not None) and (
            total_dft_energy_per_formula_unit is None
        ):
            static_job_kwargs = {}
            if self.prev_calc_dir_argname is not None:
                static_job_kwargs[self.prev_calc_dir_argname] = prev_dir
            static_job = self.static_energy_maker.make(
                structure=structure, **static_job_kwargs
            )
            jobs.append(static_job)
            total_dft_energy = static_job.output.output.energy
            static_run_job_dir = static_job.output.dir_name
            static_run_uuid = static_job.output.uuid
            prev_dir = static_job.output.dir_name
        elif total_dft_energy_per_formula_unit is not None:
            compute_total_energy_job = get_total_energy_per_cell(
                total_dft_energy_per_formula_unit, structure
            )
            jobs.append(compute_total_energy_job)
            total_dft_energy = compute_total_energy_job.output

        displacements = generate_phonon_displacements(
            structure=structure,
            supercell_matrix=supercell_matrix,
            displacement=self.displacement,
            sym_reduce=self.sym_reduce,
            symprec=self.symprec,
            use_symmetrized_structure=self.use_symmetrized_structure,
            kpath_scheme=self.kpath_scheme,
            code=self.code,
        )
        jobs.append(displacements)

        displacement_calcs = run_phonon_displacements(
            displacements=displacements.output,
            structure=structure,
            supercell_matrix=supercell_matrix,
            phonon_maker=self.phonon_displacement_maker,
            socket=self.socket,
            prev_dir_argname=self.prev_calc_dir_argname,
            prev_dir=prev_dir,
        )
        jobs.append(displacement_calcs)

        born_run_job_dir = None
        born_run_uuid = None
        if self.born_maker is not None and (born is None or epsilon_static is None):
            born_kwargs = {}
            if self.prev_calc_dir_argname is not None:
                born_kwargs[self.prev_calc_dir_argname] = prev_dir
            born_job = self.born_maker.make(structure, **born_kwargs)
            jobs.append(born_job)

            epsilon_static = born_job.output.calcs_reversed[0].output.epsilon_static
            born = born_job.output.calcs_reversed[0].output.outcar["born"]
            born_run_job_dir = born_job.output.dir_name
            born_run_uuid = born_job.output.uuid

        phonon_collect = generate_frequencies_eigenvectors(
            supercell_matrix=supercell_matrix,
            displacement=self.displacement,
            sym_reduce=self.sym_reduce,
            symprec=self.symprec,
            use_symmetrized_structure=self.use_symmetrized_structure,
            kpath_scheme=self.kpath_scheme,
            code=self.code,
            structure=structure,
            displacement_data=displacement_calcs.output,
            epsilon_static=epsilon_static,
            born=born,
            total_dft_energy=total_dft_energy,
            static_run_job_dir=static_run_job_dir,
            static_run_uuid=static_run_uuid,
            born_run_job_dir=born_run_job_dir,
            born_run_uuid=born_run_uuid,
            optimization_run_job_dir=optimization_run_job_dir,
            optimization_run_uuid=optimization_run_uuid,
            create_thermal_displacements=self.create_thermal_displacements,
            store_force_constants=self.store_force_constants,
            **self.generate_frequencies_eigenvectors_kwargs,
        )

        jobs.append(phonon_collect)

        return Flow(jobs, phonon_collect.output)

    @property
    @abstractmethod
    def prev_calc_dir_argname(self) -> str | None:
        """Name of argument informing static maker of previous calculation directory.

        As this differs between different DFT codes (e.g., VASP, CP2K), it
        has been left as a property to be implemented by the inheriting class.

        Note: this is only applicable if a relax_maker is specified; i.e., two
        calculations are performed for each ordering (relax -> static)
        """
