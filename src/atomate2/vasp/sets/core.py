
from __future__ import annotations

import logging
import warnings
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np
from pymatgen.core.periodic_table import Element

try:
    from pymatgen.io.vasp.sets import LobsterSet  # type: ignore[attr-defined]
except ImportError:
    from pymatgen.io.lobster.sets import LobsterSet  # type: ignore[attr-defined]

from atomate2.vasp.sets.base import VaspInputGenerator

if TYPE_CHECKING:
    from emmet.core.math import Vector3D
    from pymatgen.core import Structure
    from pymatgen.io.vasp import Kpoints


logger = logging.getLogger(__name__)




@dataclass
class RelaxSetGenerator(VaspInputGenerator):

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class RelaxConstVolSetGenerator(VaspInputGenerator):

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class TightRelaxSetGenerator(VaspInputGenerator):

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class TightRelaxConstVolSetGenerator(VaspInputGenerator):

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class StaticSetGenerator(VaspInputGenerator):

    lepsilon: bool = False
    lcalcpol: bool = False

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class NonSCFSetGenerator(VaspInputGenerator):

    mode: str = "line"
    dedos: float = 0.02
    reciprocal_density: float = 100
    reciprocal_density_metal: float = 400
    line_density: float = 20
    optics: bool = False
    nbands_factor: float = 1.2
    auto_ispin: bool = True
    remove_magmoms: bool = False

    def __post_init__(self) -> None:
        """Ensure mode is set correctly."""
        super().__post_init__()
        self.mode = self.mode.lower()

        supported_modes = ("line", "uniform", "boltztrap")
        if self.mode not in supported_modes:
            raise ValueError(f"Supported modes are: {', '.join(supported_modes)}")

    @property
    def kpoints_updates(self) -> dict | Kpoints:
        pass

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class HSERelaxSetGenerator(VaspInputGenerator):

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class HSETightRelaxSetGenerator(VaspInputGenerator):

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class HSEStaticSetGenerator(VaspInputGenerator):

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class HSEBSSetGenerator(VaspInputGenerator):

    mode: str = "gap"
    dedos: float = 0.02
    reciprocal_density: float = 64
    line_density: float = 20
    zero_weighted_reciprocal_density: float = 100
    optics: bool = False
    nbands_factor: float = 1.2
    added_kpoints: list[Vector3D] = field(default_factory=list)
    auto_ispin: bool = True
    remove_magmoms: bool = False

    def __post_init__(self) -> None:
        """Ensure mode is set correctly."""
        super().__post_init__()

        self.mode = self.mode.lower()
        supported_modes = ("line", "uniform", "gap", "uniform_dense")
        if self.mode not in supported_modes:
            raise ValueError(f"Supported modes are: {', '.join(supported_modes)}")

    @property
    def kpoints_updates(self) -> dict | Kpoints:
        pass

    @property
    def incar_updates(self) -> dict:
        pass


@dataclass
class ElectronPhononSetGenerator(VaspInputGenerator):

    temperatures: tuple[float, ...] = (
        0,
        100,
        200,
        300,
        400,
        500,
        600,
        700,
        800,
        900,
        1000,
    )
    reciprocal_density: float = 64
    auto_ispin: bool = True

    @property
    def incar_updates(self) -> dict:
        pass

    @property
    def kpoints_updates(self) -> dict | Kpoints:
        pass


@dataclass
class MDSetGenerator(VaspInputGenerator):

    ensemble: str = "nvt"
    start_temp: float = 300
    end_temp: float = 300
    nsteps: int = 1000
    time_step: float = 2
    auto_ispin: bool = True

    @property
    def incar_updates(self) -> dict:
        pass

    @staticmethod
    def _get_ensemble_defaults(structure: Structure, ensemble: str) -> dict[str, Any]:
        """Get default params for the ensemble."""
        n_types = getattr(structure, "n_elems", None)
        if n_types is None:
            n_types = structure.ntypesp

        defaults = {
            "nve": {"MDALGO": 1, "ISIF": 2, "ANDERSEN_PROB": 0.0},
            "nvt": {"MDALGO": 2, "ISIF": 2, "SMASS": 0},
            "npt": {
                "MDALGO": 3,
                "ISIF": 3,
                "LANGEVIN_GAMMA": [10] * n_types,
                "LANGEVIN_GAMMA_L": 1,
                "PMASS": 10,
                "PSTRESS": 0,
            },
        }

        try:
            return defaults[ensemble.lower()]  # type: ignore[return-value]
        except KeyError as err:
            supported = tuple(defaults)
            raise ValueError(f"Expect {ensemble=} to be one of {supported}") from err


@dataclass
class LobsterTightStaticSetGenerator(LobsterSet):

    reciprocal_density: int = 400

    @property
    def incar_updates(self) -> dict[str, Any]:
        pass


@dataclass
class NebSetGenerator(VaspInputGenerator):

    auto_ismear: bool = False
    auto_kspacing: bool = False
    inherit_incar: bool = False
    num_images: int = 1
    climbing_image: bool = True

    @property
    def incar_updates(self) -> dict:
        pass
