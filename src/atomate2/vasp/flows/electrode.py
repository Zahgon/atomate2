
from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from pymatgen.io.vasp.outputs import Chgcar

from atomate2.common.flows import electrode as electrode_flows
from atomate2.utils.path import strip_hostname

if TYPE_CHECKING:
    from pymatgen.io.vasp.outputs import VolumetricData

logger = logging.getLogger(__name__)


class ElectrodeInsertionMaker(electrode_flows.ElectrodeInsertionMaker):

    @staticmethod
    def get_charge_density(prev_dir: Path | str) -> VolumetricData:
        """Get the charge density of a structure.

        Parameters
        ----------
        prev_dir:
            The previous directory where the static calculation was performed.

        Returns
        -------
            The charge density.
        """
        prev_dir = Path(strip_hostname(prev_dir))
        aeccar0 = Chgcar.from_file(prev_dir / "AECCAR0.gz")
        aeccar2 = Chgcar.from_file(prev_dir / "AECCAR2.gz")
        return aeccar0 + aeccar2

    def update_static_maker(self) -> None:
        pass
