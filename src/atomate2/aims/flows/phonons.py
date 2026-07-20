
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2 import SETTINGS
from atomate2.aims.jobs.core import RelaxMaker, StaticMaker
from atomate2.aims.jobs.phonons import (
    PhononDisplacementMaker,
    PhononDisplacementMakerSocket,
)
from atomate2.common.flows.phonons import BasePhononMaker

if TYPE_CHECKING:
    from typing import Literal

    from atomate2.aims.jobs.base import BaseAimsMaker


@dataclass
class PhononMaker(BasePhononMaker):

    name: str = "phonon"
    sym_reduce: bool = True
    symprec: float = SETTINGS.PHONON_SYMPREC
    displacement: float = 0.01
    min_length: float | None = 20.0
    prefer_90_degrees: bool = True
    get_supercell_size_kwargs: dict = field(default_factory=dict)
    use_symmetrized_structure: Literal["primitive", "conventional"] | None = None
    create_thermal_displacements: bool = True
    generate_frequencies_eigenvectors_kwargs: dict = field(default_factory=dict)
    kpath_scheme: str = "seekpath"
    store_force_constants: bool = True
    socket: bool = False
    code: str = "aims"
    bulk_relax_maker: BaseAimsMaker | None = field(
        default_factory=RelaxMaker.full_relaxation
    )
    static_energy_maker: BaseAimsMaker | None = field(default_factory=StaticMaker)
    born_maker: BaseAimsMaker | None = None
    phonon_displacement_maker: BaseAimsMaker | None = None

    def __post_init__(self) -> None:
        """Set the default phonon_displacement_maker.

        Set the displacement maker based on whether the socket communicator is used
        """
        if self.phonon_displacement_maker is None:
            if self.socket:
                self.phonon_displacement_maker = PhononDisplacementMakerSocket()
            else:
                self.phonon_displacement_maker = PhononDisplacementMaker()

    @property
    def prev_calc_dir_argname(self) -> str:
        pass
