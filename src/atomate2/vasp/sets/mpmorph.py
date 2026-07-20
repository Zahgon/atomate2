
from __future__ import annotations

from dataclasses import dataclass

from pymatgen.io.vasp.sets import MPMDSet

from atomate2.vasp.sets.core import MDSetGenerator


@dataclass
class MPMorphMDSetGenerator(MPMDSet):

    auto_ismear: bool = False
    auto_kspacing: bool = True
    auto_ispin: bool = False
    auto_lreal: bool = False
    inherit_incar: bool | None = False
    ensemble: str = "nvt"
    spin_polarized: bool = False
    time_step: float = 2
    nsteps: int = 2000

    @property
    def incar_updates(self) -> dict:
        pass
