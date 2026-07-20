
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from atomate2.common.flows.anharmonicity import BaseAnharmonicityMaker

if TYPE_CHECKING:
    from atomate2.aims.flows.phonons import PhononMaker


@dataclass
class AnharmonicityMaker(BaseAnharmonicityMaker):

    name: str = "anharmonicity"
    phonon_maker: PhononMaker = None

    @property
    def prev_calc_dir_argname(self) -> str:
        pass
