
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2.common.flows.eos import CommonEosMaker
from atomate2.forcefields.jobs import ForceFieldRelaxMaker

if TYPE_CHECKING:
    from jobflow import Maker
    from typing_extensions import Self

    from atomate2.forcefields import MLFF


@dataclass
class ForceFieldEosMaker(CommonEosMaker):

    name: str = "Forcefield EOS Maker"
    initial_relax_maker: Maker = field(default_factory=ForceFieldRelaxMaker)
    eos_relax_maker: Maker = field(
        default_factory=lambda: ForceFieldRelaxMaker(relax_cell=False)
    )
    static_maker: Maker = None

    @classmethod
    def from_force_field_name(
        cls,
        force_field_name: str | MLFF | dict,
        calculator_kwargs: dict | None = None,
        relax_initial_structure: bool = True,
        **kwargs,
    ) -> Self:
        pass
