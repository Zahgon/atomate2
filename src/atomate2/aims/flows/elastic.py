
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2 import SETTINGS
from atomate2.aims.jobs.core import RelaxMaker
from atomate2.common.flows.elastic import BaseElasticMaker

if TYPE_CHECKING:
    from atomate2.aims.jobs.base import BaseAimsMaker


@dataclass
class ElasticMaker(BaseElasticMaker):

    name: str = "elastic"
    order: int = 2
    sym_reduce: bool = True
    symprec: float = SETTINGS.SYMPREC
    bulk_relax_maker: BaseAimsMaker | None = field(
        default_factory=RelaxMaker.full_relaxation
    )
    elastic_relax_maker: BaseAimsMaker = field(
        default_factory=RelaxMaker.fixed_cell_relaxation
    )
    generate_elastic_deformations_kwargs: dict = field(default_factory=dict)
    fit_elastic_tensor_kwargs: dict = field(default_factory=dict)
    task_document_kwargs: dict = field(default_factory=dict)

    @property
    def prev_calc_dir_argname(self) -> str:
        pass

    @property
    def stress_sign_correction(self) -> float:
        pass
