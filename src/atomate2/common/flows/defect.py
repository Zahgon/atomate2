
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from jobflow import Flow, Job, Maker, OutputReference

from atomate2.common.jobs.defect import (
    bulk_supercell_calculation,
    get_ccd_documents,
    get_charged_structures,
    get_defect_entry,
    get_supercell_from_prv_calc,
    spawn_defect_q_jobs,
    spawn_energy_curve_calcs,
)

if TYPE_CHECKING:
    from pathlib import Path

    import numpy.typing as npt
    from emmet.core.tasks import TaskDoc
    from pymatgen.analysis.defects.core import Defect
    from pymatgen.core.structure import Structure
    from pymatgen.entries.computed_entries import ComputedStructureEntry

logger = logging.getLogger(__name__)

DEFAULT_DISTORTIONS = (-1, -0.15, -0.1, -0.05, 0, 0.05, 0.1, 0.15, 1)


@dataclass
class ConfigurationCoordinateMaker(Maker):

    relax_maker: Maker
    static_maker: Maker
    name: str = "config coordinate"
    distortions: tuple[float, ...] = DEFAULT_DISTORTIONS

    def make(
        self,
        structure: Structure,
        charge_state1: int,
        charge_state2: int,
    ) -> Flow:
        """Make a job for the calculation of the configuration coordinate diagram.

        Parameters
        ----------
        structure
            A structure.
        charge_state1
            The reference charge state of the defect.
        charge_state2
            The excited charge state of the defect

        Returns
        -------
        Flow
            The full workflow for the calculation of the configuration coordinate
            diagram.
        """
        if not isinstance(structure, OutputReference):
            name = f"{self.name}: {structure.formula}"
            if not (
                isinstance(charge_state1, OutputReference)
                or isinstance(charge_state2, OutputReference)
            ):
                name = (
                    f"{self.name}: {structure.formula}({charge_state1}-{charge_state2})"
                )

        charged_structures = get_charged_structures(
            structure, [charge_state1, charge_state2]
        )

        relax1: Job = self.relax_maker.make(structure=charged_structures.output[0])
        relax2: Job = self.relax_maker.make(structure=charged_structures.output[1])
        relax1.append_name(" q1")
        relax2.append_name(" q2")

        dir1 = relax1.output.dir_name
        dir2 = relax2.output.dir_name
        struct1 = relax1.output.structure
        struct2 = relax2.output.structure
        add_info1 = {"relaxed_uuid": relax1.uuid, "distorted_uuid": relax2.uuid}
        add_info2 = {"relaxed_uuid": relax2.uuid, "distorted_uuid": relax1.uuid}

        deformations1, deformations2, ccd_job = self.get_deformation_and_ccd_jobs(
            struct1, struct2, dir1, dir2, add_info1, add_info2
        )

        return Flow(
            jobs=[
                charged_structures,
                relax1,
                relax2,
                deformations1,
                deformations2,
                ccd_job,
            ],
            output=ccd_job.output,
            name=name,
        )

    def make_from_relaxed_structures(
        self,
        structure1: Structure,
        structure2: Structure,
    ) -> Flow:
        pass

    def get_deformation_and_ccd_jobs(
        self,
        struct1: Structure,
        struct2: Structure,
        dir1: str | None = None,
        dir2: str | None = None,
        add_info1: dict | None = None,
        add_info2: dict | None = None,
    ) -> tuple[Job, Job, Job]:
        """Get the deformation and CCD jobs for the given structures.

        Parameters
        ----------
        struct1: Structure
            The first structure.
        struct2: Structure
            The second structure.
        dir1: str
            The directory of the first structure.
        dir2: str
            The directory of the second structure.
        add_info1: dict
            Additional information to write
        add_info2: dict
            Additional information to write

        Returns
        -------
        deformations1: Job
            The deformation job for the first structure.
        deformations2: Job
            The deformation job for the second structure.
        ccd_job: Job
            The Job to construct the CCD document.
        """
        deformations1 = spawn_energy_curve_calcs(
            struct1,
            struct2,
            distortions=self.distortions,
            static_maker=self.static_maker,
            prev_dir=dir1,
            add_name="q1",
            add_info=add_info1,
        )

        deformations2 = spawn_energy_curve_calcs(
            struct2,
            struct1,
            distortions=self.distortions,
            static_maker=self.static_maker,
            prev_dir=dir2,
            add_name="q2",
            add_info=add_info2,
        )

        deformations1.append_name(" q1")
        deformations2.append_name(" q2")

        min_abs_index = min(
            range(len(self.distortions)), key=lambda i: abs(self.distortions[i])
        )

        ccd_job = get_ccd_documents(
            deformations1.output, deformations2.output, undistorted_index=min_abs_index
        )

        return deformations1, deformations2, ccd_job


@dataclass
class FormationEnergyMaker(Maker, ABC):

    defect_relax_maker: Maker
    bulk_relax_maker: Maker | None = None
    uc_bulk: bool = False
    name: str = "formation energy"
    relax_radius: float | str | None = None
    perturb: float | None = None
    validate_charge: bool = True
    collect_defect_entry_data: bool = False

    def __post_init__(self) -> None:
        """Apply post init updates."""
        self.validate_maker()
        if self.uc_bulk:
            if self.bulk_relax_maker is not None:
                raise ValueError("bulk_relax_maker should be None when uc_bulk is True")
            if self.collect_defect_entry_data:
                raise ValueError(
                    "collect_defect_entry_data should be False when uc_bulk is True"
                )
        else:
            self.bulk_relax_maker = self.bulk_relax_maker or self.defect_relax_maker

    def make(
        self,
        defect: Defect,
        bulk_supercell_dir: str | Path | None = None,
        supercell_matrix: npt.NDArray | None = None,
        defect_index: int | str = "",
    ) -> Flow:
        """Make a flow to calculate the formation energy diagram.

        Start a series of charged supercell relaxations from a single defect
        structure.

        Parameters
        ----------
        defect: Defect
            A `Defect` object representing the Defect we are calculating the
            formation energy diagram for.
        bulk_supercell_dir: str | Path | None
            If provided, the bulk supercell calculation will be skipped.
        supercell_matrix: NDArray | None
            The supercell transformation matrix. If None, the supercell matrix
            will be computed automatically. If `bulk_supercell_dir` is provided,
            this parameter will be ignored.
        defect_index : int | str
            Additional index to give unique names to the defect calculations.
            Useful for external bookkeeping of symmetry distinct defects.

        Returns
        -------
        flow: Flow
            The workflow to calculate the formation energy diagram.
        """
        jobs = []
        if not self.uc_bulk:
            if bulk_supercell_dir is None:
                get_sc_job = bulk_supercell_calculation(
                    uc_structure=defect.structure,
                    relax_maker=self.bulk_relax_maker,
                    sc_mat=supercell_matrix,
                    get_planar_locpot=self.get_planar_locpot,
                )
                sc_mat = get_sc_job.output["sc_mat"]
                lattice = get_sc_job.output["sc_struct"].lattice
                bulk_supercell_dir = get_sc_job.output["dir_name"]
                sc_uuid = get_sc_job.output["uuid"]
            else:
                get_sc_job = get_supercell_from_prv_calc(
                    uc_structure=defect.structure,
                    prv_calc_dir=bulk_supercell_dir,
                    sc_entry_and_locpot_from_prv=self.sc_entry_and_locpot_from_prv,
                    sc_mat_ref=supercell_matrix,
                )
                sc_mat = get_sc_job.output["sc_mat"]
                lattice = get_sc_job.output["lattice"]
                sc_uuid = get_sc_job.output["uuid"]
            jobs.append(get_sc_job)
        else:
            if bulk_supercell_dir is not None:
                raise ValueError(
                    "bulk_supercell_dir should be None when uc_bulk is True."
                    "We will be using a uc bulk calculation, so no bulk supercell "
                    "is needed."
                )
            sc_mat = supercell_matrix
            lattice = None
            sc_uuid = None

        spawn_output = spawn_defect_q_jobs(
            defect=defect,
            sc_mat=sc_mat,
            relax_maker=self.defect_relax_maker,
            relaxed_sc_lattice=lattice,
            defect_index=defect_index,
            add_info={
                "bulk_supercell_dir": bulk_supercell_dir,
                "bulk_supercell_matrix": sc_mat,
                "bulk_supercell_uuid": sc_uuid,
            },
            relax_radius=self.relax_radius,
            perturb=self.perturb,
            validate_charge=self.validate_charge,
        )

        if self.uc_bulk:
            response = spawn_output.function(
                *spawn_output.function_args, **spawn_output.function_kwargs
            )
            jobs.append(response.replace)
            output_ = response.output
        else:
            jobs.append(spawn_output)
            output_ = spawn_output.output

        if self.collect_defect_entry_data:
            collection_job = get_defect_entry(
                charge_state_summary=spawn_output.output,
                bulk_summary=get_sc_job.output,
            )
            jobs.append(collection_job)

        return Flow(
            jobs=jobs,
            output=output_,
            name=self.name,
        )

    @abstractmethod
    def sc_entry_and_locpot_from_prv(
        self, previous_dir: str
    ) -> tuple[ComputedStructureEntry, dict]:
        """Copy the output ComputedStructureEntry and Locpot from previous directory.

        Parameters
        ----------
        previous_dir: str
            The directory to copy from.

        Returns
        -------
        entry: ComputedStructureEntry
        """

    @abstractmethod
    def get_planar_locpot(self, task_doc: TaskDoc) -> dict:
        """Get the Planar Locpot from the TaskDoc.

        This is needed just in case the planar average locpot is stored in different
        part of the TaskDoc for different codes.

        Parameters
        ----------
        task_doc: TaskDoc
            The task document.

        Returns
        -------
        planar_locpot: dict
            The planar average locpot.
        """

    @abstractmethod
    def validate_maker(self) -> None:
        """Check some key settings in the relax maker.

        Since this workflow is pretty complex but allows you to use any
        relax maker, it can be easy to make mistakes in the settings.
        This method should check the most important settings and raise
        an error if something is wrong.

        Example:  For VASP, the relax maker should have:
            `ISIF = 2` and `use_structure_charge = True`
        """
