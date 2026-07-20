
from dataclasses import dataclass
from typing import Literal

from pymatgen.io.vasp.sets import MPRelaxSet


@dataclass
class ApproxNebSetGenerator(MPRelaxSet):

    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | None = False
    bandgap_tol: float = None
    force_gamma: bool = True
    auto_metal_kpoints: bool = True
    symprec: float | None = None
    set_type: Literal["image", "host"] = "host"

    def __post_init__(self) -> None:
        """Ensure correct settings for class attrs."""
        super().__post_init__()
        if self.set_type not in {"image", "host"}:
            raise ValueError(
                f'Unrecognized {self.set_type=}; must be "image" or "host".'
            )

    @property
    def incar_updates(self) -> dict:
        pass
