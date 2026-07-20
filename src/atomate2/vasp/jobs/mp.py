
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pymatgen.io.vasp.sets import (
    MP24RelaxSet,
    MP24StaticSet,
    MPRelaxSet,
    MPScanRelaxSet,
    MPScanStaticSet,
    MPStaticSet,
)

from atomate2.vasp.jobs.base import BaseVaspMaker

if TYPE_CHECKING:
    from atomate2.vasp.sets.base import VaspInputGenerator


@dataclass
class MPGGARelaxMaker(BaseVaspMaker):

    name: str = "MP GGA relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MPRelaxSet(
            force_gamma=True, auto_metal_kpoints=True, inherit_incar=False
        )
    )


@dataclass
class MPGGAStaticMaker(BaseVaspMaker):

    name: str = "MP GGA static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MPStaticSet(
            force_gamma=True, auto_metal_kpoints=True, inherit_incar=False
        )
    )


@dataclass
class MPPreRelaxMaker(BaseVaspMaker):

    name: str = "MP pre-relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MPScanRelaxSet(
            auto_ismear=False,
            inherit_incar=False,
            user_incar_settings={
                "EDIFFG": -0.05,
                "GGA": "PS",
                "LWAVE": True,
                "LCHARG": True,
                "LELF": False,  # prevents KPAR > 1
                "METAGGA": None,
            },
        )
    )


@dataclass
class MPMetaGGARelaxMaker(BaseVaspMaker):

    name: str = "MP meta-GGA relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MPScanRelaxSet(
            auto_ismear=False,
            inherit_incar=False,
            user_incar_settings={
                "GGA": None,  # unset GGA, shouldn't be set anyway but best be sure
                "LCHARG": True,
                "LWAVE": True,
                "LELF": False,  # prevents KPAR > 1
            },
        )
    )


@dataclass
class MPMetaGGAStaticMaker(BaseVaspMaker):

    name: str = "MP meta-GGA static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MPScanStaticSet(
            auto_ismear=False,
            inherit_incar=False,
            user_incar_settings={
                "ALGO": "FAST",
                "GGA": None,  # unset GGA, shouldn't be set anyway but best be sure
                "LCHARG": True,
                "LWAVE": False,
                "LVHAR": None,  # not needed, unset
                "LELF": False,  # prevents KPAR > 1
            },
        )
    )


@dataclass
class MP24PreRelaxMaker(BaseVaspMaker):

    name: str = "MP24 PBEsol pre-relaxation"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MP24RelaxSet(
            xc_functional="PBEsol", user_incar_settings={"LWAVE": True}
        )
    )


@dataclass
class MP24RelaxMaker(BaseVaspMaker):

    name: str = "MP24 r2SCAN relaxation"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MP24RelaxSet(
            xc_functional="r2SCAN", user_incar_settings={"LWAVE": True}
        )
    )


@dataclass
class MP24StaticMaker(BaseVaspMaker):

    name: str = "MP24 r2SCAN static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MP24StaticSet(
            xc_functional="r2SCAN",
            user_incar_settings={
                "LELF": True,  # want to save this data?
                "KPAR": 1,  # b/c LELF = True mandates KPAR = 1
            },
        )
    )
