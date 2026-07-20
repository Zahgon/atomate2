
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2.common.flows.approx_neb import (
    ApproxNebFromEndpointsMaker,
    CommonApproxNebMaker,
)
from atomate2.vasp.jobs.approx_neb import (
    ApproxNebHostRelaxMaker,
    ApproxNebImageRelaxMaker,
    get_charge_density,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.io.vasp.outputs import Chgcar

    from atomate2.vasp.jobs.base import BaseVaspMaker


@dataclass
class ApproxNebMaker(CommonApproxNebMaker):

    name: str = "ApproxNEB VASP"
    host_relax_maker: BaseVaspMaker | None = field(
        default_factory=ApproxNebHostRelaxMaker
    )
    image_relax_maker: BaseVaspMaker = field(default_factory=ApproxNebImageRelaxMaker)
    use_aeccar: bool = False

    def get_charge_density(self, prev_dir: str | Path) -> Chgcar:
        """Get charge density from a prior VASP calculation.

        Parameters
        ----------
        prev_dir : str or Path
            Path to the previous VASP calculation

        Returns
        -------
        pymatgen Chgcar object
        """
        return get_charge_density(prev_dir, use_aeccar=self.use_aeccar)


@dataclass
class ApproxNebSingleHopMaker(ApproxNebFromEndpointsMaker):

    image_relax_maker: BaseVaspMaker = field(default_factory=ApproxNebImageRelaxMaker)
    name: str = "VASP ApproxNEB single hop from endpoints maker"
    use_aeccar: bool = False

    def get_charge_density(self, prev_dir: str | Path) -> Chgcar:
        """Get charge density from a prior VASP calculation.

        Parameters
        ----------
        prev_dir : str or Path
            Path to the previous VASP calculation

        Returns
        -------
        pymatgen Chgcar object
        """
        return get_charge_density(prev_dir, use_aeccar=self.use_aeccar)
