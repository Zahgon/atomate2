
from __future__ import annotations

from dataclasses import dataclass, field

from pymatgen.io.vasp.inputs import Kpoints, KpointsSupportedModes

from atomate2.vasp.sets.base import VaspInputGenerator

SPECIAL_KPOINT = Kpoints(
    comment="special k-point",
    num_kpts=1,
    style=KpointsSupportedModes.Reciprocal,
    kpts=((0.25, 0.25, 0.25),),
    kpts_shift=(0, 0, 0),
    kpts_weights=[1],
)

SPECIAL_KPOINT_GAMMA = Kpoints(
    comment="special k-point",
    num_kpts=2,
    style=KpointsSupportedModes.Reciprocal,
    kpts=((0.25, 0.25, 0.25), (0.0, 0.0, 0.0)),
    kpts_shift=(0, 0, 0),
    kpts_weights=[1, 0],
)


@dataclass
class ChargeStateRelaxSetGenerator(VaspInputGenerator):

    use_structure_charge: bool = True
    user_kpoints_settings: dict | Kpoints = field(default_factory=SPECIAL_KPOINT)

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class ChargeStateStaticSetGenerator(VaspInputGenerator):

    use_structure_charge: bool = True
    user_kpoints_settings: dict | Kpoints = field(default_factory=SPECIAL_KPOINT)

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class HSEChargeStateRelaxSetGenerator(VaspInputGenerator):

    use_structure_charge: bool = True
    user_kpoints_settings: dict | Kpoints = field(default_factory=SPECIAL_KPOINT)

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class HSEChargeStateStaticSetGenerator(VaspInputGenerator):

    use_structure_charge: bool = True
    user_kpoints_settings: dict | Kpoints = field(default_factory=SPECIAL_KPOINT)

    @property
    def incar_updates(self) -> dict:
        pass
