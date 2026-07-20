
from __future__ import annotations

from dataclasses import dataclass, field

from atomate2 import SETTINGS
from atomate2.common.flows.gruneisen import BaseGruneisenMaker
from atomate2.forcefields.flows.phonons import PhononMaker
from atomate2.forcefields.jobs import ForceFieldRelaxMaker


@dataclass
class GruneisenMaker(BaseGruneisenMaker):

    name: str = "Gruneisen"
    bulk_relax_maker: ForceFieldRelaxMaker | None = field(
        default_factory=lambda: ForceFieldRelaxMaker(
            force_field_name="CHGNet", relax_kwargs={"fmax": 0.00001}
        )
    )
    code: str = "forcefields"
    const_vol_relax_maker: ForceFieldRelaxMaker = field(
        default_factory=lambda: ForceFieldRelaxMaker(
            force_field_name="CHGNet", relax_kwargs={"fmax": 0.00001}, relax_cell=False
        )
    )
    kpath_scheme: str = "seekpath"
    phonon_maker: PhononMaker = field(
        default_factory=lambda: PhononMaker(
            bulk_relax_maker=None, static_energy_maker=None
        )
    )
    perc_vol: float = 0.01
    mesh: tuple | float = 7_000
    compute_gruneisen_param_kwargs: dict = field(default_factory=dict)
    symprec: float = SETTINGS.PHONON_SYMPREC

    @property
    def prev_calc_dir_argname(self) -> None:
        pass
