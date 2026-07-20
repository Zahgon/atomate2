
from __future__ import annotations

from itertools import chain
from typing import TYPE_CHECKING

import numpy as np
from maggma.builders import Builder
from pydash import get
from pymatgen.analysis.elasticity import Deformation, Stress

from atomate2 import SETTINGS
from atomate2.common.schemas.elastic import ElasticDocument

if TYPE_CHECKING:
    from collections.abc import Generator

    from maggma.core import Store


class ElasticBuilder(Builder):

    def __init__(
        self,
        tasks: Store,
        elasticity: Store,
        query: dict = None,
        symprec: float = SETTINGS.SYMPREC,
        fitting_method: str = SETTINGS.ELASTIC_FITTING_METHOD,
        structure_match_tol: float = 1e-5,
        **kwargs,
    ) -> None:
        self.tasks = tasks
        self.elasticity = elasticity
        self.query = query or {}
        self.kwargs = kwargs
        self.symprec = symprec
        self.fitting_method = fitting_method
        self.structure_match_tol = structure_match_tol

        super().__init__(sources=[tasks], targets=[elasticity], **kwargs)

    def ensure_indexes(self) -> None:
        pass

    def get_items(self) -> Generator:
        pass

    def process_item(self, tasks: list[dict]) -> list[ElasticDocument]:
        pass

    def update_targets(self, items: list[ElasticDocument]) -> None:
        pass


def _group_deformations(tasks: list[dict], tol: float) -> list[list[dict]]:
    pass


def _get_elastic_document(
    tasks: list[dict],
    symprec: float,
    fitting_method: str,
) -> ElasticDocument:
    pass
