
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

import numpy as np
from jobflow import Flow, Maker, Response, job

from atomate2.common.jobs.eos import MPMorphPVPostProcess, _apply_strain_to_structure

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Any

    from jobflow import Job
    from pymatgen.core import Structure
    from typing_extensions import Self

    from atomate2.common.jobs.eos import EOSPostProcessor


@dataclass
class EquilibriumVolumeMaker(Maker):

    md_maker: Maker
    name: str = "Equilibrium Volume Maker"
    postprocessor: EOSPostProcessor = field(default_factory=MPMorphPVPostProcess)
    initial_strain: float | tuple[float, float] = 0.2
    min_strain: float = 0.5
    max_attempts: int | None = 20

    def __post_init__(self) -> None:
        """Ensure required class attributes are set."""
        if self.md_maker is None:
            raise ValueError("You must specify `md_maker` to use this flow.")

    @job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
        working_outputs: dict[str, Any] | None = None,
    ) -> Flow:
        """
        Run an NVT+EOS equilibration flow.

        Parameters
        ----------
        structure : Structure
            structure to equilibrate
        prev_dir : str | Path | None (default)
            path to copy files from
        working_outputs : dict or None
            contains the outputs of the flow as it recursively updates

        Returns
        -------
        .Flow, an MPMorph flow
        """
        if working_outputs is None:
            if isinstance(self.initial_strain, float | int):
                self.initial_strain = (
                    -abs(self.initial_strain),
                    abs(self.initial_strain),
                )
            elif (
                not isinstance(self.initial_strain, tuple | list | np.array)
                or len(self.initial_strain) != 2
            ):
                raise ValueError(
                    "`initial_strain` should either be a float, to set "
                    "a symmetric linear strain of ± `initial_strain`, or a two-element "
                    "tuple / list to explicitly set linear strain values, "
                    f"not {self.initial_strain}."
                )

            linear_strain = np.linspace(
                *self.initial_strain, self.postprocessor.min_data_points
            )
            working_outputs = {
                "relax": {key: [] for key in ("energy", "volume", "stress", "pressure")}
            }

        else:
            self.postprocessor.fit(working_outputs)
            working_outputs = dict(self.postprocessor.results)
            flow_output = {"working_outputs": working_outputs.copy(), "structure": None}
            for k in ("pressure",):
                working_outputs["relax"].pop(k, None)

            if (v0 := working_outputs.get("V0")) is None:
                return Response(output=flow_output, stop_children=True)

            vmin = working_outputs.get("Vmin")
            vmax = working_outputs.get("Vmax")

            max_attempts_reached = len(working_outputs["relax"]["volume"]) >= (
                (self.max_attempts or np.inf) + self.postprocessor.min_data_points
            )

            if (vmin <= v0 <= vmax) or max_attempts_reached:
                flow_output["structure"] = structure.copy()
                flow_output["structure"].scale_lattice(v0)  # type: ignore[attr-defined]
                return flow_output

            v_ref = vmax if v0 > vmax else vmin
            eps_0 = (v0 / v_ref) ** (1.0 / 3.0) - 1.0
            linear_strain = [np.sign(eps_0) * (abs(eps_0) + self.min_strain)]

        deformation_matrices = [np.eye(3) * (1.0 + eps) for eps in linear_strain]
        deformed_structures = _apply_strain_to_structure(
            structure, deformation_matrices
        )

        eos_jobs = []
        for index in range(len(deformation_matrices)):
            md_job = self.md_maker.make(
                deformed_structures[index].final_structure,
                prev_dir=None,
            )

            relaxed_vol = len(working_outputs["relax"]["volume"])
            md_job.name = f"{self.name} {md_job.name} {relaxed_vol + 1}"

            working_outputs["relax"]["energy"].append(md_job.output.output.energy)
            working_outputs["relax"]["volume"].append(md_job.output.structure.volume)
            working_outputs["relax"]["stress"].append(md_job.output.output.stress)
            eos_jobs.append(md_job)

        recursive = self.make(
            structure,
            prev_dir=None,
            working_outputs=working_outputs,
        )

        new_eos_flow = Flow([*eos_jobs, recursive], output=recursive.output)

        return Response(replace=new_eos_flow, output=recursive.output)


@dataclass
class MPMorphMDMaker(Maker, ABC):

    production_md_maker: Maker
    name: str = "Base MPMorph MD"
    equilibrium_volume_maker: Maker | None = None
    quench_maker: FastQuenchMaker | SlowQuenchMaker | None = None

    def __post_init__(self) -> None:
        """Ensure required class attributes are set."""
        if self.production_md_maker is None:
            raise ValueError("You must set `production_md_maker` to use this flow.")

    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> Flow:
        """
        Create an MPMorph equilibration workflow.

        Converegence and quench steps are optional, and may be used
        to equilibrate the cell volume (useful for high temperature
        production runs of structures extracted from Materials Project)
        and to quench the structure from high to low temperature
        (e.g. amorphous structures), respectively.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing series of molecular dynamics run (and relax+static).
        """
        flow_jobs = []

        if self.equilibrium_volume_maker is not None:
            convergence_flow = self.equilibrium_volume_maker.make(
                structure, prev_dir=prev_dir
            )
            flow_jobs.append(convergence_flow)

            structure = convergence_flow.output["structure"]

        self.production_md_maker.name = self.name + " production run"
        production_run = self.production_md_maker.make(structure, prev_dir=prev_dir)
        flow_jobs.append(production_run)

        if self.quench_maker:
            quench_flow = self.quench_maker.make(
                production_run.output.structure,
                prev_dir=production_run.output.dir_name,
            )
            flow_jobs += [quench_flow]

        return Flow(
            flow_jobs,
            output=production_run.output,
            name=self.name,
        )

    @classmethod
    @abstractmethod
    def from_temperature_and_steps(
        cls,
        temperature: float,
        n_steps_convergence: int = 5000,
        n_steps_production: int = 10000,
        end_temp: float | None = None,
        md_maker: Maker = None,
        quench_maker: FastQuenchMaker | SlowQuenchMaker | None = None,
    ) -> Self:
        """
        Create an MPMorph flow from a temperature and number of steps.

        This is a convenience class constructor. The user need only
        input the desired temperature and steps for convergence / production
        MD runs.

        Parameters
        ----------
        temperature : float
            The (starting) temperature
        n_steps_convergence : int = 5000
            The number of steps used in MD runs for equilibrating structures.
        n_steps_production : int = 10000
            The number of steps used in MD production runs.
        end_temp : float or None
            If a float, the temperature to ramp down to in the production run.
            If None (default), set to `temperature`.
        base_md_maker : Maker
            The Maker used to start MD runs.
        quench_maker : SlowQuenchMaker or FastQuenchMaker or None
            SlowQuenchMaker - MDMaker that quenches structure from
                high to low temperature
            FastQuenchMaker - DoubleRelaxMaker + Static that
                "quenches" structure at 0K
        """
        raise NotImplementedError


@dataclass
class FastQuenchMaker(Maker):

    relax_maker: Maker
    static_maker: Maker
    name: str = "fast quench"
    relax_maker2: Maker | None = None

    def __post_init__(self) -> None:
        """Ensure required class attributes are set."""
        for attr in ("relax_maker", "static_maker"):
            if getattr(self, attr, None) is None:
                raise ValueError(
                    f"You must specify {attr} to use this flow. "
                    "Only `relax_maker2` is optional."
                )

    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> Flow:
        """
        Create a fast quench flow with relax and static makers.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing series of relax and static runs.
        """
        jobs: list[Job] = []

        relax1 = self.relax_maker.make(structure, prev_dir=prev_dir)
        jobs += [relax1]
        structure = relax1.output.structure
        prev_dir = relax1.output.dir_name

        if self.relax_maker2 is not None:
            relax1.name += " 1"
            relax2 = self.relax_maker2.make(structure, prev_dir=prev_dir)
            relax2.name += " 2"
            jobs += [relax2]
            structure = relax2.output.structure
            prev_dir = relax2.output.dir_name

        static = self.static_maker.make(structure, prev_dir=prev_dir)
        jobs += [static]
        return Flow(
            jobs,
            output=static.output,
            name=self.name,
        )


@dataclass
class SlowQuenchMaker(Maker, ABC):

    md_maker: Maker
    name: str = "slow quench"
    quench_start_temperature: float = 3000
    quench_end_temperature: float = 500
    quench_temperature_step: float = 500
    quench_n_steps: int = 1000
    descent_method: Literal["stepwise", "linear with hold"] = "stepwise"

    def __post_init__(self) -> None:
        """Ensure required class attributes are set."""
        if self.md_maker is None:
            raise ValueError("You must specify `md_maker` to use this flow.")

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """
        Create a slow quench flow with md maker.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing series of relax and static runs.
        """
        md_jobs: list[Job] = []
        for temp in np.arange(
            self.quench_start_temperature,
            self.quench_end_temperature,
            -self.quench_temperature_step,
        ):
            prev_dir = (
                None
                if temp == self.quench_start_temperature
                else md_jobs[-1].output.dir_name
            )
            if self.descent_method == "stepwise":
                md_job = self.call_md_maker(
                    structure,
                    temp=temp,
                    prev_dir=prev_dir,
                )

            elif (
                self.descent_method == "linear with hold"
            ):  # TODO: Work in Progress; needs testing
                md_job_linear = self.call_md_maker(
                    structure,
                    temp=[temp, temp - self.quench_temperature_step],  # type: ignore[arg-type]
                    prev_dir=prev_dir,
                )

                md_job = self.call_md_maker(
                    md_job_linear.output.structure,
                    temp=temp - self.quench_temperature_step,
                    prev_dir=md_job_linear.output.dir_name,
                )

                md_jobs.append(md_job_linear)

            md_jobs.append(md_job)

            structure = md_job.output.structure

        return Flow(
            md_jobs,
            output=md_jobs[-1].output,
            name=self.name,
        )

    @abstractmethod
    def call_md_maker(
        self,
        structure: Structure,
        temp: float,
        prev_dir: str | Path | None = None,
    ) -> Flow | Job:
        """Call MD maker for slow quench.

        To be implemented in subclasses.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        temp : float
            The temperature in Kelvin.
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from.

        Returns
        -------
        A slow quench .Flow or .Job
        """
        raise NotImplementedError
