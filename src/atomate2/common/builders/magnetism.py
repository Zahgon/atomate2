
from __future__ import annotations

from typing import TYPE_CHECKING

from emmet.core.utils import jsanitize
from maggma.builders import Builder
from monty.serialization import MontyDecoder
from pymatgen.analysis.structure_matcher import StructureMatcher

from atomate2.common.schemas.magnetism import MagneticOrderingsDocument

if TYPE_CHECKING:
    from collections.abc import Iterator

    from maggma.core import Store


class MagneticOrderingsBuilder(Builder):

    def __init__(
        self,
        tasks: Store,
        magnetic_orderings: Store,
        query: dict = None,
        structure_match_stol: float = 0.3,
        structure_match_ltol: float = 0.2,
        structure_match_angle_tol: float = 5,
        **kwargs,
    ) -> None:
        self.tasks = tasks
        self.magnetic_orderings = magnetic_orderings
        self.query = query or {}
        self.structure_match_stol = structure_match_stol
        self.structure_match_ltol = structure_match_ltol
        self.structure_match_angle_tol = structure_match_angle_tol

        self.kwargs = kwargs

        super().__init__(sources=[tasks], targets=[magnetic_orderings], **kwargs)

    def ensure_indexes(self) -> None:
        pass

    def get_items(self) -> Iterator[list[dict]]:
        pass

    def process_item(self, tasks: list[dict]) -> list[MagneticOrderingsDocument]:
        pass

    def update_targets(self, items: list[MagneticOrderingsDocument]) -> None:
        pass


def _group_orderings(
    tasks: list[dict], ltol: float, stol: float, angle_tol: float
) -> list[list[dict]]:
    pass
