
from __future__ import annotations

import logging
import os
from pathlib import Path

from emmet.core.qc_tasks import TaskDoc
from pymatgen.apps.borg.hive import AbstractDrone

logger = logging.getLogger(__name__)


class QChemDrone(AbstractDrone):

    def __init__(self, **task_document_kwargs) -> None:
        self.task_document_kwargs = task_document_kwargs

    def assimilate(self, path: str | Path | None = None) -> TaskDoc:
        pass

    def get_valid_paths(self, path: tuple[str, list[str], list[str]]) -> list[str]:
        pass
