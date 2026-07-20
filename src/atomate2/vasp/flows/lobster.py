
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Flow, Maker
from monty.dev import requires

from atomate2.common.jobs.utils import remove_workflow_files
from atomate2.lobster.jobs import LobsterMaker
from atomate2.vasp.flows.core import DoubleRelaxMaker, UniformBandStructureMaker
from atomate2.vasp.jobs.core import NonSCFMaker, RelaxMaker, StaticMaker
from atomate2.vasp.jobs.lobster import (
    get_basis_infos,
    get_lobster_jobs,
    update_user_incar_settings_maker,
)
from atomate2.vasp.sets.core import NonSCFSetGenerator, StaticSetGenerator

try:
    import ijson
    from lobsterpy.cohp.analyze import Analysis
    from lobsterpy.cohp.describe import Description
except ImportError:
    ijson = None
    Analysis = None
    Description = None

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core import Structure

    from atomate2.vasp.jobs.base import BaseVaspMaker


LOBSTER_UNIFORM_MAKER = UniformBandStructureMaker(
    name="uniform lobster structure",
    static_maker=StaticMaker(
        input_set_generator=StaticSetGenerator(
            user_kpoints_settings={"reciprocal_density": 100},
            user_incar_settings={
                "EDIFF": 1e-7,
                "LAECHG": False,
                "LVTOT": False,
                "LREAL": False,
                "ALGO": "Normal",
                "LWAVE": False,
            },
        )
    ),
    bs_maker=NonSCFMaker(
        input_set_generator=NonSCFSetGenerator(
            user_kpoints_settings={"reciprocal_density": 400},
            user_incar_settings={
                "LWAVE": True,
                "ISYM": 0,
            },
        ),
        task_document_kwargs={"parse_dos": False, "parse_bandstructure": False},
    ),
)


@dataclass
class VaspLobsterMaker(Maker):

    name: str = "lobster"
    relax_maker: BaseVaspMaker | None = field(
        default_factory=lambda: DoubleRelaxMaker.from_relax_maker(RelaxMaker())
    )
    lobster_static_maker: BaseVaspMaker = field(
        default_factory=lambda: LOBSTER_UNIFORM_MAKER
    )
    lobster_maker: LobsterMaker | None = field(default_factory=LobsterMaker)
    delete_wavecars: bool = True
    address_min_basis: str | None = None
    address_max_basis: str | None = None

    @requires(
        Analysis,
        "This flow requires lobsterpy and ijson to function properly. "
        "Please reinstall atomate2 using atomate2[lobster]",
    )
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> Flow:
        """Make flow to calculate bonding properties.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure. Please start with a structure
            that is nearly fully optimized as the internal optimizers
            have very strict settings!
        prev_dir : str or Path or None
            A previous vasp calculation directory to use for copying outputs.
        """
        jobs = []

        optimization_dir = None
        optimization_uuid = None
        if self.relax_maker is not None:
            optimization = self.relax_maker.make(structure, prev_dir=prev_dir)
            jobs.append(optimization)
            structure = optimization.output.structure
            optimization_dir = optimization.output.dir_name
            optimization_uuid = optimization.output.uuid
            prev_dir = optimization_dir

        basis_infos = get_basis_infos(
            structure=structure,
            vasp_maker=self.lobster_static_maker,
            address_min_basis=self.address_min_basis,
            address_max_basis=self.address_max_basis,
        )
        jobs.append(basis_infos)

        lobster_static = update_user_incar_settings_maker(
            self.lobster_static_maker,
            basis_infos.output["nbands"],
            structure,
            prev_dir,
        )
        jobs.append(lobster_static)
        lobster_static_dir = lobster_static.output.dir_name
        lobster_static_uuid = lobster_static.output.uuid

        lobster_jobs = get_lobster_jobs(
            lobster_maker=self.lobster_maker,
            basis_dict=basis_infos.output["basis_dict"],
            optimization_dir=optimization_dir,
            optimization_uuid=optimization_uuid,
            static_dir=lobster_static_dir,
            static_uuid=lobster_static_uuid,
        )
        jobs.append(lobster_jobs)

        if self.delete_wavecars:
            delete_wavecars = remove_workflow_files(
                [lobster_jobs.output["lobster_dirs"], lobster_static.output.dir_name],
                ["WAVECAR"],
                allow_zpath=True,
            )
            delete_wavecars.name = "delete_lobster_wavecar"
            jobs.append(delete_wavecars)

        return Flow(jobs, output=lobster_jobs.output)
