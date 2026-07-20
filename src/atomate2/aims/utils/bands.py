
from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from pymatgen.symmetry.bandstructure import HighSymmKpath

if TYPE_CHECKING:
    from pymatgen.core.structure import Structure


class _SegmentDict(TypedDict):
    coords: list[list[float]]
    labels: list[str]
    length: int


def prepare_band_input(structure: Structure, density: float = 20) -> list:
    pass
