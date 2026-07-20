
from __future__ import annotations

from dataclasses import dataclass, field

from atomate2 import SETTINGS
from atomate2.common.flows.gruneisen import BaseGruneisenMaker
from atomate2.vasp.flows.core import DoubleRelaxMaker
from atomate2.vasp.flows.phonons import PhononMaker
from atomate2.vasp.jobs.core import TightRelaxConstVolMaker, TightRelaxMaker



@dataclass
class GruneisenMaker(BaseGruneisenMaker):

    name: str = "Gruneisen"
    bulk_relax_maker: TightRelaxMaker | None = field(
        default_factory=lambda: DoubleRelaxMaker.from_relax_maker(TightRelaxMaker())
    )
    code: str = "vasp"

    const_vol_relax_maker: TightRelaxMaker | None = field(
        default_factory=lambda: DoubleRelaxMaker.from_relax_maker(
            TightRelaxConstVolMaker()
        )
    )
    kpath_scheme: str = "seekpath"
    phonon_maker: PhononMaker | None = field(
        default_factory=lambda: PhononMaker(
            bulk_relax_maker=None, static_energy_maker=None
        )
    )
    vol: float = 0.01
    mesh: tuple | float = 7_000
    compute_gruneisen_param_kwargs: dict = field(default_factory=dict)
    symprec = SETTINGS.PHONON_SYMPREC

    @property
    def prev_calc_dir_argname(self) -> str:
        pass
