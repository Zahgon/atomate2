
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from jobflow import Maker, Response, job
from monty.serialization import dumpfn
from pymatgen.io.aims.sets.base import AimsInputGenerator
from pymatgen.util.due import Doi, due

from atomate2 import SETTINGS
from atomate2.aims.files import (
    cleanup_aims_outputs,
    copy_aims_outputs,
    write_aims_input_set,
)
from atomate2.aims.run import run_aims, should_stop_children
from atomate2.aims.schemas.task import AimsTaskDoc
from atomate2.common.files import gzip_output_folder

if TYPE_CHECKING:
    from pymatgen.core import Molecule, Structure

logger = logging.getLogger(__name__)

_INPUT_FILES = [
    "geometry.in",
    "control.in",
]

_OUTPUT_FILES = ["aims.out", "geometry.in.next_step", "hessian.aims", "*.cube", "*.csc"]

_FILES_TO_ZIP = _INPUT_FILES + _OUTPUT_FILES


@due.dcite(Doi("10.1016/j.cpc.2009.06.022"), description="FHI-AIMS")
@dataclass
class BaseAimsMaker(Maker):

    name: str = "base"
    input_set_generator: AimsInputGenerator = field(default_factory=AimsInputGenerator)
    write_input_set_kwargs: dict[str, Any] = field(default_factory=dict)
    copy_aims_kwargs: dict[str, Any] = field(default_factory=dict)
    run_aims_kwargs: dict[str, Any] = field(default_factory=dict)
    task_document_kwargs: dict[str, Any] = field(default_factory=dict)
    stop_children_kwargs: dict[str, Any] = field(default_factory=dict)
    write_additional_data: dict[str, Any] = field(default_factory=dict)
    store_output_data: bool = True

    @job
    def make(
        self,
        structure: Structure | Molecule,
        prev_dir: str | Path | None = None,
    ) -> Response:
        """Run an FHI-aims calculation.

        Parameters
        ----------
        structure : Structure or Molecule
            A pymatgen Structure object to create the calculation for.
        prev_dir : str or Path or None
            A previous FHI-aims calculation directory to copy output files from.
        """
        if prev_dir is not None:
            copy_aims_outputs(prev_dir, **self.copy_aims_kwargs)

        self.write_input_set_kwargs["prev_dir"] = prev_dir
        write_aims_input_set(
            structure, self.input_set_generator, **self.write_input_set_kwargs
        )

        for filename, data in self.write_additional_data.items():
            dumpfn(data, filename.replace(":", "."))

        run_aims(**self.run_aims_kwargs)

        task_doc = AimsTaskDoc.from_directory(Path.cwd(), **self.task_document_kwargs)
        task_doc.task_label = self.name

        stop_children = should_stop_children(task_doc, **self.stop_children_kwargs)

        cleanup_aims_outputs(directory=Path.cwd())

        gzip_output_folder(
            directory=Path.cwd(),
            setting=SETTINGS.VASP_ZIP_FILES,
            files_list=_FILES_TO_ZIP,
        )

        return Response(
            stop_children=stop_children,
            output=task_doc if self.store_output_data else None,
        )
