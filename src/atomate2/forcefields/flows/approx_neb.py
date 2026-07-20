
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from pymatgen.io.common import VolumetricData
from pymatgen.io.vasp.outputs import Chgcar
from typing_extensions import Self

from atomate2.common.flows.approx_neb import ApproxNebFromEndpointsMaker
from atomate2.forcefields.jobs import ForceFieldRelaxMaker
from atomate2.forcefields.utils import MLFF


@dataclass
class ForceFieldApproxNebFromEndpointsMaker(ApproxNebFromEndpointsMaker):

    image_relax_maker: ForceFieldRelaxMaker
    name: str = "MLFF ApproxNEB single hop from endpoints maker"

    def get_charge_density(
        self, prev_dir_or_chgcar: str | Path | Chgcar | Sequence[str | Path | Chgcar]
    ) -> VolumetricData:
        """Obtain charge density from a specified path, CHGCAR, or list of them.

        Parameters
        ----------
        prev_dir_or_chgcar : str or Path or pymatgen .Chgcar, or a list of these
            Path(s) to the CHGCAR/AECCAR* file(s) or the object(s) themselves.

        Returns
        -------
            VolumetricData
                The charge density
        """
        if isinstance(prev_dir_or_chgcar, str | Path | Chgcar):
            prev_dir_or_chgcar = [prev_dir_or_chgcar]

        for idx, obj in enumerate(prev_dir_or_chgcar):
            chg = Chgcar.from_file(obj) if isinstance(obj, str | Path) else obj
            if idx == 0:
                charge_density = chg
            else:
                charge_density += chg
        return charge_density

    @classmethod
    def from_force_field_name(
        cls,
        force_field_name: str | MLFF | dict,
        calculator_kwargs: dict | None = None,
        **kwargs,
    ) -> Self:
        pass
