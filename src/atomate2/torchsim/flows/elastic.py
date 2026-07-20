
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2 import SETTINGS
from atomate2.common.flows.elastic import BaseElasticMaker
from atomate2.torchsim.units import EV_PER_A3_TO_KBAR

if TYPE_CHECKING:
    from atomate2.torchsim import TorchSimOptimizeMaker


@dataclass
class ElasticMaker(BaseElasticMaker):

    name: str = "elastic"
    order: int = 2
    sym_reduce: bool = True
    symprec: float = SETTINGS.SYMPREC
    bulk_relax_maker: TorchSimOptimizeMaker | None = None
    elastic_relax_maker: TorchSimOptimizeMaker | None = None  # constant volume
    max_failed_deformations: int | float | None = None
    generate_elastic_deformations_kwargs: dict = field(default_factory=dict)
    fit_elastic_tensor_kwargs: dict = field(default_factory=dict)
    task_document_kwargs: dict = field(default_factory=dict)
    socket: bool = True

    @property
    def prev_calc_dir_argname(self) -> str | None:
        """Name of argument informing static maker of previous calculation directory.

        As this differs between different DFT codes (e.g., VASP, CP2K), it
        has been left as a property to be implemented by the inheriting class.

        Note: this is only applicable if a relax_maker is specified; i.e., two
        calculations are performed for each ordering (relax -> static)
        """

    @property
    def stress_sign_correction(self) -> float:
        pass
