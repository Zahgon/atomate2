
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from emmet.core.tasks import TaskDoc
from jobflow import Flow, Maker, OutputReference
from jobflow.core.maker import recursive_call

from atomate2.common.flows import defect as defect_flows
from atomate2.vasp.flows.core import DoubleRelaxMaker
from atomate2.vasp.jobs.core import RelaxMaker, StaticMaker
from atomate2.vasp.jobs.defect import calculate_finite_diff
from atomate2.vasp.sets.defect import (
    SPECIAL_KPOINT,
    ChargeStateRelaxSetGenerator,
    ChargeStateStaticSetGenerator,
    HSEChargeStateRelaxSetGenerator,
)

if TYPE_CHECKING:
    from pymatgen.core.structure import Structure
    from pymatgen.entries.computed_entries import ComputedStructureEntry

    from atomate2.common.schemas.defects import CCDDocument
    from atomate2.vasp.jobs.base import BaseVaspMaker

logger = logging.getLogger(__name__)


DEFECT_INCAR_SETTINGS = {
    "ISMEAR": 0,
    "LWAVE": True,
    "SIGMA": 0.05,
    "KSPACING": None,
    "ENCUT": 500,
}
DEFECT_KPOINT_SETTINGS = {"reciprocal_density": 64}

DEFECT_RELAX_GENERATOR = ChargeStateRelaxSetGenerator(
    use_structure_charge=True,
    user_incar_settings=DEFECT_INCAR_SETTINGS,
    user_kpoints_settings=DEFECT_KPOINT_SETTINGS,
)
DEFECT_STATIC_GENERATOR = ChargeStateStaticSetGenerator(
    user_incar_settings=DEFECT_INCAR_SETTINGS,
    user_kpoints_settings=DEFECT_KPOINT_SETTINGS,
)
HSE_DOUBLE_RELAX = DoubleRelaxMaker(
    relax_maker1=RelaxMaker(
        input_set_generator=ChargeStateRelaxSetGenerator(
            user_kpoints_settings=SPECIAL_KPOINT
        )
    ),
    relax_maker2=RelaxMaker(
        input_set_generator=HSEChargeStateRelaxSetGenerator(
            user_kpoints_settings=SPECIAL_KPOINT
        ),
        task_document_kwargs={"store_volumetric_data": ["locpot"]},
        copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR",)},
    ),
)
GRID_KEYS = ["NGX", "NGY", "NGZ", "NGXF", "NGYF", "NGZF"]


@dataclass
class FormationEnergyMaker(defect_flows.FormationEnergyMaker):

    defect_relax_maker: BaseVaspMaker = field(
        default_factory=lambda: RelaxMaker(
            input_set_generator=ChargeStateRelaxSetGenerator(
                user_kpoints_settings=SPECIAL_KPOINT
            ),
            task_document_kwargs={"average_locpot": True},
        )
    )
    bulk_relax_maker: BaseVaspMaker | None = None
    name: str = "formation energy"

    def sc_entry_and_locpot_from_prv(
        self, previous_dir: str
    ) -> tuple[ComputedStructureEntry, dict]:
        """Copy the output structure from previous directory.

        Read the vasprun.xml file from the previous directory
        and return the structure.

        Parameters
        ----------
        previous_dir: str
            The directory to copy from.

        Returns
        -------
        ComputedStructureEntry
        """
        task_doc = TaskDoc.from_directory(previous_dir)
        return task_doc.structure_entry, task_doc.calcs_reversed[0].output.locpot

    def get_planar_locpot(self, task_doc: TaskDoc) -> dict:
        """Get the planar-averaged electrostatic potential."""
        return task_doc.calcs_reversed[0].output.locpot

    def validate_maker(self) -> None:
        pass


@dataclass
class ConfigurationCoordinateMaker(defect_flows.ConfigurationCoordinateMaker):

    relax_maker: BaseVaspMaker = field(
        default_factory=lambda: RelaxMaker(
            input_set_generator=DEFECT_RELAX_GENERATOR,
        )
    )
    static_maker: BaseVaspMaker = field(
        default_factory=lambda: StaticMaker(input_set_generator=DEFECT_STATIC_GENERATOR)
    )
    name: str = "config coordinate"


@dataclass
class NonRadiativeMaker(Maker):

    ccd_maker: ConfigurationCoordinateMaker
    name: str = "non-radiative"

    def make(
        self,
        structure: Structure,
        charge_state1: int,
        charge_state2: int,
    ) -> Flow:
        """Create the job for Non-Radiative defect capture.

        Make a job for the calculation of the configuration coordinate diagram.
        Also calculate the el-phon matrix elements for 1-D special phonon.

        Parameters
        ----------
        structure
            A structure.
        charge_state1
            The reference charge state of the defect.
        charge_state2
            The excited charge state of the defect
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

        flow = self.ccd_maker.make(
            structure=structure,
            charge_state1=charge_state1,
            charge_state2=charge_state2,
        )
        ccd: CCDDocument = flow.output

        finite_diff_job1 = calculate_finite_diff(
            distorted_calc_dirs=ccd.static_dirs1,
            ref_calc_index=ccd.relaxed_index1,
            run_vasp_kwargs=self.ccd_maker.static_maker.run_vasp_kwargs,
        )
        finite_diff_job2 = calculate_finite_diff(
            distorted_calc_dirs=ccd.static_dirs2,
            ref_calc_index=ccd.relaxed_index2,
            run_vasp_kwargs=self.ccd_maker.static_maker.run_vasp_kwargs,
        )

        finite_diff_job1.name = "finite diff q1"
        finite_diff_job2.name = "finite diff q2"

        output = {
            charge_state1: finite_diff_job1.output,
            charge_state2: finite_diff_job2.output,
        }
        return Flow(
            jobs=[flow, finite_diff_job1, finite_diff_job2], output=output, name=name
        )
