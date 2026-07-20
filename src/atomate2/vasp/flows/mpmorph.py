
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Response

from atomate2.common.flows.mpmorph import (
    EquilibriumVolumeMaker,
    FastQuenchMaker,
    MPMorphMDMaker,
    SlowQuenchMaker,
)
from atomate2.vasp.flows.md import MultiMDMaker
from atomate2.vasp.jobs.mpmorph import (
    BaseMPMorphMDMaker,
    FastQuenchVaspMaker,
    SlowQuenchVaspMaker,
)
from atomate2.vasp.powerups import update_user_incar_settings

if TYPE_CHECKING:
    from jobflow import Maker
    from typing_extensions import Self

    from atomate2.vasp.jobs.base import BaseVaspMaker
    from atomate2.vasp.jobs.md import MDMaker


@dataclass
class MPMorphVaspMDMaker(MPMorphMDMaker):

    name: str = "MP Morph VASP MD Maker"
    equilibrium_volume_maker: EquilibriumVolumeMaker = field(
        default_factory=lambda: EquilibriumVolumeMaker(md_maker=BaseMPMorphMDMaker())
    )
    production_md_maker: MDMaker | MultiMDMaker = field(
        default_factory=BaseMPMorphMDMaker
    )

    @classmethod
    def from_temperature_and_steps(  # type: ignore[override]
        cls,
        temperature: float,
        n_steps_convergence: int = 5000,
        n_steps_production: int = 10000,
        end_temp: float | None = None,
        md_maker: Maker = BaseMPMorphMDMaker,
        n_steps_per_production_run: int | None = None,
        quench_maker: FastQuenchMaker | SlowQuenchMaker | None = None,
    ) -> Self:
        pass


@dataclass
class MPMorphSlowQuenchVaspMDMaker(MPMorphVaspMDMaker):

    name: str = "MP Morph VASP MD Maker Slow Quench"
    equilibrium_volume_maker: EquilibriumVolumeMaker = field(
        default_factory=lambda: EquilibriumVolumeMaker(md_maker=BaseMPMorphMDMaker())
    )
    production_md_maker: MDMaker = field(default_factory=BaseMPMorphMDMaker)
    quench_maker: SlowQuenchVaspMaker = field(
        default_factory=lambda: SlowQuenchVaspMaker(
            BaseMPMorphMDMaker(name="Slow Quench VASP Maker"),
            quench_n_steps=1000,
            quench_temperature_step=500,
            quench_end_temperature=500,
            quench_start_temperature=3000,
            descent_method="stepwise",
        )
    )


@dataclass
class MPMorphFastQuenchVaspMDMaker(MPMorphVaspMDMaker):

    name: str = "MP Morph VASP MD Maker Fast Quench"
    equilibrium_volume_maker: EquilibriumVolumeMaker = field(
        default_factory=lambda: EquilibriumVolumeMaker(md_maker=BaseMPMorphMDMaker())
    )
    production_md_maker: MDMaker = field(default_factory=BaseMPMorphMDMaker)
    quench_maker: BaseVaspMaker = field(default_factory=FastQuenchVaspMaker)
