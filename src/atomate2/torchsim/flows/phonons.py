
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from atomate2 import SETTINGS
from atomate2.common.flows.phonons import BasePhononMaker

if TYPE_CHECKING:
    from atomate2.torchsim.core import TorchSimOptimizeMaker, TorchSimStaticMaker


@dataclass
class PhononMaker(BasePhononMaker):

    name: str = "phonon"
    sym_reduce: bool = True
    symprec: float = SETTINGS.PHONON_SYMPREC
    displacement: float = 0.01
    min_length: float | None = 20.0
    max_length: float | None = None
    prefer_90_degrees: bool = True
    get_supercell_size_kwargs: dict = field(default_factory=dict)
    use_symmetrized_structure: Literal["primitive", "conventional"] | None = None
    bulk_relax_maker: TorchSimOptimizeMaker | None = None
    static_energy_maker: TorchSimStaticMaker | None = None
    phonon_displacement_maker: TorchSimStaticMaker | None = None
    generate_frequencies_eigenvectors_kwargs: dict = field(default_factory=dict)
    create_thermal_displacements: bool = False
    kpath_scheme: str = "seekpath"
    code: str = "torchsim"
    store_force_constants: bool = True
    born_maker: TorchSimStaticMaker | None = None
    socket: bool = True

    @property
    def prev_calc_dir_argname(self) -> None:
        """Name of argument informing static maker of previous calculation directory.

        As this differs between different DFT codes (e.g., VASP, CP2K), it
        has been left as a property to be implemented by the inheriting class.

        Note: this is only applicable if a relax_maker is specified; i.e., two
        calculations are performed for each ordering (relax -> static)
        """
