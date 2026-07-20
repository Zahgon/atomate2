
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from emmet.core.mobility.migrationgraph import MigrationGraphDoc
from jobflow import Flow, Maker, OnMissing
from pymatgen.util.due import Doi, due

from atomate2.common.jobs.approx_neb import (
    collate_images_single_hop,
    collate_results,
    get_endpoints_and_relax,
    get_images_and_relax,
)

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any, Literal

    from jobflow import Job
    from pymatgen.core import Structure
    from pymatgen.io.common import VolumetricData
    from pymatgen.util.typing import CompositionLike


@due.dcite(Doi("https://doi.org/10.1063/1.4960790"), description="ApproxNEB")
@dataclass
class CommonApproxNebMaker(Maker):

    name: str = "ApproxNEB"
    host_relax_maker: Maker | None = None
    image_relax_maker: Maker = None
    endpoint_relax_maker: Maker | None = None
    selective_dynamics_scheme: Literal["fix_two_atoms"] | None = "fix_two_atoms"
    min_hop_distance: float | bool = True

    def make(
        self,
        host_structure: Structure,
        working_ion: str,
        inserted_coords_dict: dict | list,
        inserted_coords_combo: list,
        n_images: int = 5,
        min_images_per_hop: int | None = 3,
        prev_dir: str | Path | None = None,
    ) -> Flow:
        """
        Make an ApproxNEB flow.

        Parameters
        ----------
        host_structure: Structure
            the (supercell) structure of the empty host with no working ion
        working_ion: str
            the mobile species in ApproxNEB
        inserted_coords_dict: dict or list
            a dictionary containing fractional site coords (endpoints)
            for working ions in the simulation cell.
        inserted_coords_combo: list
            a list of combo strings "a+b" to designate run calculations between
            endpoints a and b
            inserted_coords_dict should contain all indices specified
            in inserted_coords_combo
        n_images: int = 5
            number of intermediate images for the ApproxNEB calculation
        min_images_per_hop : int or None, default = 3
            If an int, the minimum number of image calculations per hop that
            must succeed to mark a hop as successfully calculated.
        selective_dynamics: str
            the scheme for adding selective dynamics to image relaxations

        Returns
        -------
        Flow
            A flow performing AppoxNEB calculations
        """
        if isinstance(inserted_coords_dict, list):
            inserted_coords_dict = dict(enumerate(inserted_coords_dict))

        unique_ep_idxs = set()
        for combo in inserted_coords_combo:
            unique_ep_idxs.update([int(idx) for idx in combo.split("+")])
        if len(
            missing_idxs := unique_ep_idxs.difference(
                {int(idx) for idx in inserted_coords_dict}
            )
        ):
            raise ValueError(
                "Missing working ion insertion indices in `inserted_coords_dict`: "
                f"{', '.join([str(idx) for idx in missing_idxs])}"
            )

        jobs: list[Job] = []

        if self.host_relax_maker:
            host_relax_job = self.host_relax_maker.make(
                host_structure, prev_dir=prev_dir
            )
            host_relax_job.append_name("host structure ", prepend=True)
            jobs += [host_relax_job]
            host_structure = host_relax_job.output.structure
            prev_dir = host_relax_job.output.dir_name

        ep_relax_jobs = get_endpoints_and_relax(
            host_structure=host_structure,
            working_ion=working_ion,
            endpoint_coords=inserted_coords_dict,
            inserted_coords_combo=inserted_coords_combo,
            relax_maker=self.endpoint_relax_maker or self.image_relax_maker,
        )

        image_relax_jobs = get_images_and_relax(
            working_ion=working_ion,
            ep_output=ep_relax_jobs.output,
            inserted_combo_list=inserted_coords_combo,
            n_images=n_images,
            charge_density_path=prev_dir,
            get_charge_density=self.get_charge_density,
            relax_maker=self.image_relax_maker,
            selective_dynamics_scheme=self.selective_dynamics_scheme,
            min_hop_distance=self.min_hop_distance,
        )

        collect_output = collate_results(
            host_structure,
            working_ion,
            ep_relax_jobs.output,
            image_relax_jobs.output,
            min_images_per_hop=min_images_per_hop,
        )

        collect_output.config.on_missing_references = OnMissing.NONE

        return Flow(
            [*jobs, ep_relax_jobs, image_relax_jobs, collect_output],
            output=collect_output.output,
        )

    def make_from_migration_graph_doc(
        self,
        migration_graph_doc: MigrationGraphDoc,
        n_images: int = 5,
        prev_dir: str | Path | None = None,
        atomate_compat_labels: bool = False,
    ) -> Flow:
        pass

    def get_charge_density(self, *args, **kwargs) -> VolumetricData:
        """Get charge density, to be implemented in subclasses.

        Returns
        -------
        pymatgen VolumetricData
        """
        raise NotImplementedError


@dataclass
class ApproxNebFromEndpointsMaker(Maker):

    image_relax_maker: Maker
    name: str = "ApproxNEB single hop from endpoints maker"
    selective_dynamics_scheme: Literal["fix_two_atoms"] | None = "fix_two_atoms"
    min_images_per_hop: int | None = 3
    min_hop_distance: float | bool = True

    def make(
        self,
        working_ion: CompositionLike,
        end_point_structures: list[Structure] | tuple[Structure, Structure],
        charge_density_path: str | Path,
        n_images: int = 5,
        prev_dir: str | Path | None = None,
    ) -> Flow:
        """
        Run an ApproxNEB flow for a single hop.

        working_ion : CompositionLike
            The element which migrates.
        end_point_structures : list of pymatgen .Structure
            The two endpoint structures
        charge_density_path: str or .Path
            Path to the directory containing the charge density file(s).
        n_images: int = 5
            number of images for the ApproxNEB calculation
        prev_dir : str, .Path, or None
            If not None, the path to a previous calculation to
            copy outputs from.

        Returns
        -------
        Flow
            A flow performing an AppoxNEB calculation for a single hop.
        """
        if len(end_point_structures) != 2:
            raise ValueError(
                "Specify only two endpoint structures, "
                f"{len(end_point_structures)} structures were supplied."
            )

        ep_jobs: list[Job] = []
        ep_output: dict[str, dict[str, Any]] = {}
        for idx, ep in enumerate(end_point_structures):
            job = self.image_relax_maker.make(ep, prev_dir=prev_dir)
            job.name = f"ApproxNEB relax endpoint {idx}"
            ep_output[str(idx)] = {
                "initial_structure": ep,
                "structure": job.output.structure,
                "energy": job.output.output.energy,
            }
            ep_jobs.append(job)

        image_calcs = get_images_and_relax(
            working_ion=working_ion,
            ep_output=ep_output,
            inserted_combo_list=["0+1"],
            n_images=n_images,
            charge_density_path=charge_density_path,
            get_charge_density=self.get_charge_density,
            relax_maker=self.image_relax_maker,
            selective_dynamics_scheme=self.selective_dynamics_scheme,
            min_hop_distance=self.min_hop_distance,
        )

        collate_job = collate_images_single_hop(
            working_ion=working_ion,
            endpoint_calc_output=[ep_output[str(idx)] for idx in range(2)],
            image_calc_output=image_calcs.output["0+1"],
            min_images_per_hop=self.min_images_per_hop,
        )
        collate_job.config.on_missing_references = OnMissing.NONE
        return Flow([*ep_jobs, image_calcs, collate_job], output=collate_job.output)

    def get_charge_density(self, prev_dir: str | Path) -> VolumetricData:
        """Obtain charge density from a specified path.

        Parameters
        ----------
        prev_dir : str or Path
            Path to the calculation containing the previous charge density.

        Returns
        -------
            VolumetricData
                The charge density
        """
        raise NotImplementedError
