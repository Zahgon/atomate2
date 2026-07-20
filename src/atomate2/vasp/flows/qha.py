
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from atomate2.common.flows.qha import CommonQhaMaker
from atomate2.vasp.flows.phonons import PhononMaker
from atomate2.vasp.jobs.core import TightRelaxMaker
from atomate2.vasp.jobs.eos import EosRelaxMaker
from atomate2.vasp.sets.core import TightRelaxSetGenerator


@dataclass
class QhaMaker(CommonQhaMaker):

    name: str = "VASP QHA Maker"
    initial_relax_maker: TightRelaxMaker | None = field(default_factory=TightRelaxMaker)
    eos_relax_maker: TightRelaxMaker | None = field(
        default_factory=lambda: EosRelaxMaker(
            input_set_generator=TightRelaxSetGenerator(
                user_incar_settings={"ISIF": 2},
            )
        )
    )
    phonon_maker: PhononMaker | None = field(
        default_factory=lambda: PhononMaker(bulk_relax_maker=None)
    )
    linear_strain: tuple[float, float] = (-0.05, 0.05)
    number_of_frames: int = 6
    pressure: float | None = None
    t_max: float | None = None
    ignore_imaginary_modes: bool = False
    skip_analysis: bool = False
    eos_type: Literal["vinet", "birch_murnaghan", "murnaghan"] = "vinet"
    analyze_free_energy_kwargs: dict = field(default_factory=dict)

    @property
    def prev_calc_dir_argname(self) -> str:
        pass
