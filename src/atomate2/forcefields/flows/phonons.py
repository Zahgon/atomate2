
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from atomate2 import SETTINGS
from atomate2.common.flows.phonons import BasePhononMaker
from atomate2.forcefields.jobs import ForceFieldRelaxMaker, ForceFieldStaticMaker
from atomate2.forcefields.utils import MLFF

if TYPE_CHECKING:
    from typing_extensions import Self

    from atomate2.forcefields import MLFF


@dataclass
class PhononMaker(BasePhononMaker):

    name: str = "phonon"
    sym_reduce: bool = True
    symprec: float = SETTINGS.PHONON_SYMPREC
    displacement: float = 0.01
    min_length: float | None = 20.0
    prefer_90_degrees: bool = True
    max_length: float | None = None
    get_supercell_size_kwargs: dict = field(default_factory=dict)
    use_symmetrized_structure: Literal["primitive", "conventional"] | None = None
    bulk_relax_maker: ForceFieldRelaxMaker | None = field(
        default_factory=lambda: ForceFieldRelaxMaker(
            force_field_name="CHGNet", relax_kwargs={"fmax": 1e-5}
        )
    )
    static_energy_maker: ForceFieldStaticMaker | None = field(
        default_factory=lambda: ForceFieldStaticMaker(force_field_name="CHGNet")
    )
    phonon_displacement_maker: ForceFieldStaticMaker = field(
        default_factory=lambda: ForceFieldStaticMaker(force_field_name="CHGNet")
    )
    create_thermal_displacements: bool = False
    generate_frequencies_eigenvectors_kwargs: dict = field(default_factory=dict)
    kpath_scheme: str = "seekpath"
    store_force_constants: bool = True
    code: str = "forcefields"
    born_maker: ForceFieldStaticMaker | None = None

    @property
    def prev_calc_dir_argname(self) -> None:
        pass

    @property
    def mlff(self) -> MLFF:
        pass

    @property
    def ase_calculator_name(self) -> str:
        pass

    @classmethod
    def from_force_field_name(
        cls,
        force_field_name: str | MLFF | dict,
        calculator_kwargs: dict | None = None,
        relax_initial_structure: bool = True,
        **kwargs,
    ) -> Self:
        pass
