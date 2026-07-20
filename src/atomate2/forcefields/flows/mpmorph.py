
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2.common.flows.mpmorph import (
    EquilibriumVolumeMaker,
    FastQuenchMaker,
    MPMorphMDMaker,
    SlowQuenchMaker,
)
from atomate2.forcefields.jobs import ForceFieldRelaxMaker, ForceFieldStaticMaker
from atomate2.forcefields.md import ForceFieldMDMaker

if TYPE_CHECKING:
    from pathlib import Path

    from jobflow import Flow, Job
    from pymatgen.core import Structure
    from typing_extensions import Self

    from atomate2.forcefields import MLFF


@dataclass
class MPMorphMLFFMDMaker(MPMorphMDMaker):

    name: str = "MP Morph MLFF MD Maker"
    equilibrium_volume_maker: EquilibriumVolumeMaker | None = None
    production_md_maker: ForceFieldMDMaker = field(default_factory=ForceFieldMDMaker)
    quench_maker: FastQuenchMaker | SlowQuenchMaker | None = None

    @classmethod
    def from_temperature_and_steps(
        cls,
        temperature: float,
        n_steps_convergence: int = 5000,
        n_steps_production: int = 1000,
        end_temp: float | None = None,
        md_maker: ForceFieldMDMaker = None,
        quench_maker: FastQuenchMaker | SlowQuenchMaker | None = None,
    ) -> Self:
        pass


@dataclass
class SlowQuenchMLFFMDMaker(SlowQuenchMaker):

    name: str = "ForceField slow quench"
    md_maker: ForceFieldMDMaker = field(default_factory=ForceFieldMDMaker)

    def call_md_maker(
        self,
        structure: Structure,
        temp: float | tuple[float, float],
        prev_dir: str | Path | None = None,
    ) -> Flow | Job:
        """Call the MD maker to create the MD jobs for MLFF Only."""
        self.md_maker = self.md_maker.update_kwargs(
            update={
                "name": f"Slow quench MLFF MD Maker {temp}K",
                "temperature": temp,
                "n_steps": self.quench_n_steps,
            }
        )
        return self.md_maker.make(structure=structure, prev_dir=prev_dir)


@dataclass
class FastQuenchMLFFMDMaker(FastQuenchMaker):

    name: str = "ForceField fast quench"
    relax_maker: ForceFieldRelaxMaker = field(default_factory=ForceFieldRelaxMaker)
    relax_maker2: ForceFieldRelaxMaker = field(default_factory=ForceFieldRelaxMaker)
    static_maker: ForceFieldStaticMaker = field(default_factory=ForceFieldStaticMaker)

    @classmethod
    def from_force_field_name(
        cls,
        force_field_name: str | MLFF | dict,
        calculator_kwargs: dict | None = None,
    ) -> Self:
        pass
