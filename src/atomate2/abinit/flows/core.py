
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Flow, Maker

from atomate2.abinit.jobs.core import (
    LineNonSCFMaker,
    RelaxMaker,
    StaticMaker,
    UniformNonSCFMaker,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core.structure import Structure

    from atomate2.abinit.jobs.base import BaseAbinitMaker


@dataclass
class BandStructureMaker(Maker):

    name: str = "band structure - dos"
    static_maker: BaseAbinitMaker = field(default_factory=StaticMaker)
    bs_maker: BaseAbinitMaker | None = field(default_factory=LineNonSCFMaker)
    dos_maker: BaseAbinitMaker | None = field(default_factory=UniformNonSCFMaker)

    def make(
        self,
        structure: Structure,
        restart_from: str | Path | None = None,
    ) -> Flow:
        """Create a band structure flow.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        restart_from : str or Path or None
            One previous directory to restart from.

        Returns
        -------
        Flow
            A band structure flow.
        """
        static_job = self.static_maker.make(structure, restart_from=restart_from)
        jobs = [static_job]

        if self.dos_maker:
            uniform_job = self.dos_maker.make(
                prev_outputs=static_job.output.dir_name,
            )
            jobs.append(uniform_job)

        if self.bs_maker:
            line_job = self.bs_maker.make(
                prev_outputs=static_job.output.dir_name,
            )
            jobs.append(line_job)

        return Flow(jobs, name=self.name)


@dataclass
class RelaxFlowMaker(Maker):

    name: str = "relaxation"
    relaxation_makers: list[Maker] = field(
        default_factory=lambda: [
            RelaxMaker.ionic_relaxation(),
            RelaxMaker.full_relaxation(),
        ]
    )

    def make(
        self,
        structure: Structure | None = None,
        restart_from: str | Path | None = None,
    ) -> Flow:
        """Create a relaxation flow.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        restart_from : str or Path or None
            One previous directory to restart from.

        Returns
        -------
        Flow
            A relaxation flow.
        """
        relax_job1 = self.relaxation_makers[0].make(
            structure=structure, restart_from=restart_from
        )
        jobs = [relax_job1]
        for rlx_maker in self.relaxation_makers[1:]:
            rlx_job = rlx_maker.make(restart_from=jobs[-1].output.dir_name)
            jobs.append(rlx_job)
        return Flow(jobs, output=jobs[-1].output, name=self.name)

    @classmethod
    def ion_ioncell_relaxation(cls, *args, **kwargs) -> Flow:
        pass
