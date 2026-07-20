
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pymatgen.io.vasp.sets import MatPESStaticSet

from atomate2.vasp.jobs.base import BaseVaspMaker

if TYPE_CHECKING:
    from atomate2.vasp.sets.base import VaspInputGenerator


@dataclass
class MatPesGGAStaticMaker(BaseVaspMaker):

    name: str = "MatPES GGA static"
    input_set_generator: VaspInputGenerator = field(default_factory=MatPESStaticSet)


@dataclass
class MatPesMetaGGAStaticMaker(BaseVaspMaker):

    name: str = "MatPES meta-GGA static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MatPESStaticSet(
            xc_functional="R2SCAN", user_incar_settings={"GGA": None}
        )
    )
