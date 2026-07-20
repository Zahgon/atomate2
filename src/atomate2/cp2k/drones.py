
from __future__ import annotations

import logging
import os
from pathlib import Path

from pymatgen.apps.borg.hive import AbstractDrone

from atomate2.cp2k.schemas.task import TaskDocument

logger = logging.getLogger(__name__)


class Cp2kDrone(AbstractDrone):

    def __init__(self, **task_document_kwargs) -> None:
        self.task_document_kwargs = task_document_kwargs

    def assimilate(self, path: str | Path | None = None) -> TaskDocument:
        pass

    def get_valid_paths(self, path: tuple[str, list[str], list[str]]) -> list[str]:
        pass
