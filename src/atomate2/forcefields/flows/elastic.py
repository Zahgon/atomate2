
from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2 import SETTINGS
from atomate2.common.flows.elastic import BaseElasticMaker
from atomate2.forcefields.jobs import ForceFieldRelaxMaker

if TYPE_CHECKING:
    from typing import Any

    from typing_extensions import Self

    from atomate2.forcefields import MLFF

_DEFAULT_RELAX_KWARGS: dict[str, Any] = {
    "force_field_name": "CHGNet",
    "relax_kwargs": {"fmax": 0.00001},
    "fix_symmetry": True,
}


@dataclass
class ElasticMaker(BaseElasticMaker):

    name: str = "elastic"
    order: int = 2
    sym_reduce: bool = True
    symprec: float = SETTINGS.SYMPREC
    bulk_relax_maker: ForceFieldRelaxMaker | None = field(
        default_factory=lambda: ForceFieldRelaxMaker(
            relax_cell=True, **_DEFAULT_RELAX_KWARGS
        )
    )
    elastic_relax_maker: ForceFieldRelaxMaker | None = field(
        default_factory=lambda: ForceFieldRelaxMaker(
            relax_cell=False, **_DEFAULT_RELAX_KWARGS
        )
    )  # constant volume relaxation
    max_failed_deformations: int | float | None = None
    generate_elastic_deformations_kwargs: dict = field(default_factory=dict)
    fit_elastic_tensor_kwargs: dict = field(default_factory=dict)
    task_document_kwargs: dict = field(default_factory=dict)

    @property
    def prev_calc_dir_argname(self) -> str | None:
        """Name of argument informing static maker of previous calculation directory.

        As this differs between different DFT codes (e.g., VASP, CP2K), it
        has been left as a property to be implemented by the inheriting class.

        Note: this is only applicable if a relax_maker is specified; i.e., two
        calculations are performed for each ordering (relax -> static)
        """

    @classmethod
    def from_force_field_name(
        cls,
        force_field_name: str | MLFF | dict,
        calculator_kwargs: dict | None = None,
        relax_initial_structure: bool = True,
        **kwargs,
    ) -> Self:
        pass
