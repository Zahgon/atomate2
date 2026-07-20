
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from atomate2.common.flows.qha import CommonQhaMaker
from atomate2.forcefields.flows.phonons import PhononMaker
from atomate2.forcefields.jobs import ForceFieldRelaxMaker

if TYPE_CHECKING:
    from typing_extensions import Self

    from atomate2.forcefields import MLFF


@dataclass
class ForceFieldQhaMaker(CommonQhaMaker):

    name: str = "Forcefield QHA Maker"
    initial_relax_maker: ForceFieldRelaxMaker | None = None
    eos_relax_maker: ForceFieldRelaxMaker | None = None
    phonon_maker: PhononMaker = None
    linear_strain: tuple[float, float] = (-0.05, 0.05)
    number_of_frames: int = 6
    pressure: float | None = None
    t_max: float | None = None
    ignore_imaginary_modes: bool = False
    skip_analysis: bool = False
    eos_type: Literal["vinet", "birch_murnaghan", "murnaghan"] = "vinet"
    analyze_free_energy_kwargs: dict = field(default_factory=dict)

    @property
    def prev_calc_dir_argname(self) -> None:
        pass

    @classmethod
    def from_force_field_name(
        cls,
        force_field_name: str | MLFF | dict,
        calculator_kwargs: dict | None = None,
        relax_initial_structure: bool = True,
        run_eos_flow: bool = True,
        **kwargs,
    ) -> Self:
        pass


@dataclass
class CHGNetQhaMaker(ForceFieldQhaMaker):

    name: str = "CHGNet QHA Maker"
    phonon_maker: PhononMaker = field(
        default_factory=lambda: PhononMaker(bulk_relax_maker=None)
    )
    initial_relax_maker: ForceFieldRelaxMaker | None = field(
        default_factory=lambda: ForceFieldRelaxMaker(force_field_name="CHGNet")
    )
    eos_relax_maker: ForceFieldRelaxMaker | None = field(
        default_factory=lambda: ForceFieldRelaxMaker(
            force_field_name="CHGNet", relax_cell=False, relax_kwargs={"fmax": 1e-5}
        )
    )
