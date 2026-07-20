
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from pymatgen.io.vasp.sets import MPRelaxSet, MPScanRelaxSet, VaspInputSet

from atomate2 import SETTINGS

if TYPE_CHECKING:
    from pymatgen.core import Structure
    from pymatgen.io.vasp import Kpoints
    from pymatgen.io.vasp.sets import UserPotcarFunctional

_BASE_VASP_SET = MPScanRelaxSet()._config_dict | {"KPOINTS": {}}  # noqa: SLF001
_ATOMATE2_BASE_VASP_SET_UPDATES = {
    "INCAR": {
        "ALGO": "Fast",
        "GGA": "PS",
        "LREAL": False,
        "KSPACING": None,
        "METAGGA": None,
        **{
            k: v
            for k, v in MPRelaxSet()._config_dict["INCAR"].items()  # noqa: SLF001
            if k.startswith("LDAU")
        },
    },
    "KPOINTS": {"reciprocal_density": 64, "reciprocal_density_metal": 200},
    "POTCAR": {
        "Be": "Be",
        "Bi": "Bi_d",
        "Cu": "Cu",
        "Eu": "Eu_2",
        "Fe": "Fe",
        "Gd": "Gd_3",
        "Mg": "Mg",
        "Mo": "Mo_sv",
        "Nb": "Nb_sv",
        "Ni": "Ni",
        "Os": "Os",
        "Re": "Re",
        "Ti": "Ti_sv",
        "V": "V_sv",
    },
}
for k, updates in _ATOMATE2_BASE_VASP_SET_UPDATES.items():
    for g, v in updates.items():
        if v is None:
            _BASE_VASP_SET[k].pop(g)
        else:
            _BASE_VASP_SET[k][g] = v


@dataclass
class VaspInputGenerator(VaspInputSet):

    structure: Structure | None = None
    config_dict: dict = field(default_factory=lambda: _BASE_VASP_SET)
    files_to_transfer: dict = field(default_factory=dict)
    user_incar_settings: dict = field(default_factory=dict)
    user_kpoints_settings: dict = field(default_factory=dict)
    user_potcar_settings: dict = field(default_factory=dict)
    constrain_total_magmom: bool = False
    sort_structure: bool = True
    user_potcar_functional: UserPotcarFunctional = None
    force_gamma: bool = True
    reduce_structure: Literal["niggli", "LLL"] | None = None
    vdw: str | None = None
    use_structure_charge: bool = False
    standardize: bool = False
    sym_prec: float = SETTINGS.SYMPREC
    international_monoclinic: bool = True
    validate_magmom: bool = True
    inherit_incar: bool | list[str] = SETTINGS.VASP_INHERIT_INCAR
    auto_ismear: bool = True
    auto_ispin: bool = False
    auto_lreal: bool = False
    auto_metal_kpoints: bool = True
    auto_kspacing: bool = False
    bandgap_tol: float = SETTINGS.BANDGAP_TOL
    bandgap: float | None = None
    prev_incar: str | dict | None = None
    prev_kpoints: str | Kpoints | None = None
