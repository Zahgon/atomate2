
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pymatgen.io.vasp.sets import MPRelaxSet, MPScanRelaxSet

from atomate2.vasp.sets.base import VaspInputGenerator

if TYPE_CHECKING:
    from pymatgen.io.vasp import Kpoints


@dataclass
class EosSetGenerator(VaspInputGenerator):

    force_gamma: bool = True
    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | list[str] = False

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class MPLegacyEosRelaxSetGenerator(VaspInputGenerator):

    config_dict: dict = field(default_factory=lambda: MPRelaxSet.CONFIG)
    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | list[str] = False

    @property
    def incar_updates(self) -> dict:
        pass

    @property
    def kpoints_updates(self) -> dict | Kpoints:
        pass


@dataclass
class MPLegacyEosStaticSetGenerator(EosSetGenerator):

    config_dict: dict = field(default_factory=lambda: MPRelaxSet.CONFIG)
    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | list[str] = False

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class MPGGAEosRelaxSetGenerator(VaspInputGenerator):

    config_dict: dict = field(default_factory=lambda: MPScanRelaxSet.CONFIG)
    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | list[str] = False

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class MPGGAEosStaticSetGenerator(EosSetGenerator):

    config_dict: dict = field(default_factory=lambda: MPScanRelaxSet.CONFIG)
    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | list[str] = False

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class MPMetaGGAEosStaticSetGenerator(VaspInputGenerator):

    config_dict: dict = field(default_factory=lambda: MPScanRelaxSet.CONFIG)
    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | list[str] = False

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class MPMetaGGAEosRelaxSetGenerator(VaspInputGenerator):

    config_dict: dict = field(default_factory=lambda: MPScanRelaxSet.CONFIG)
    bandgap_tol: float = 1e-4
    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | list[str] = False

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class MPMetaGGAEosPreRelaxSetGenerator(VaspInputGenerator):

    config_dict: dict = field(default_factory=lambda: MPScanRelaxSet.CONFIG)
    bandgap_tol: float = 1e-4
    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool | list[str] = False

    @property
    def incar_updates(self) -> dict:
        pass
