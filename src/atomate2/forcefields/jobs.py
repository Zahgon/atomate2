
from __future__ import annotations

import logging
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import job

from atomate2.ase.jobs import AseRelaxMaker
from atomate2.forcefields.schemas import ForceFieldTaskDocument
from atomate2.forcefields.utils import _FORCEFIELD_DATA_OBJECTS, MLFF, ForceFieldMixin

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pymatgen.core.structure import Molecule, Structure

    from atomate2.forcefields.schemas import ForceFieldMoleculeTaskDocument

logger = logging.getLogger(__name__)


def forcefield_job(method: Callable) -> job:
    pass


@dataclass
class ForceFieldRelaxMaker(ForceFieldMixin, AseRelaxMaker):

    name: str = "Force field relax"
    force_field_name: str | MLFF | dict = MLFF.Forcefield
    relax_cell: bool = True
    relax_shape: bool = False
    fix_symmetry: bool = False
    symprec: float | None = 1e-2
    steps: int = 500
    relax_kwargs: dict = field(default_factory=dict)
    optimizer_kwargs: dict = field(default_factory=dict)
    calculator_kwargs: dict = field(default_factory=dict)
    task_document_kwargs: dict = field(default_factory=dict)

    @forcefield_job
    def make(
        self,
        structure: Molecule | Structure | list[Molecule | Structure],
        prev_dir: str | Path | None = None,
    ) -> (
        ForceFieldTaskDocument
        | ForceFieldMoleculeTaskDocument
        | list[ForceFieldTaskDocument | ForceFieldMoleculeTaskDocument]
    ):
        """
        Perform a relaxation of a structure using a force field.

        Parameters
        ----------
        structure: .Molecule or .Structure, or a list thereof
            pymatgen molecule(s) or structure(s)
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
                added to match the method signature of other makers.

        Returns
        -------
            ForceFieldTaskDocument, ForceFieldMoleculeTaskDocument, or a list thereof
        """
        if len(self.task_document_kwargs) > 0:
            warnings.warn(
                "`task_document_kwargs` is now deprecated, please use the top-level "
                "attributes `ionic_step_data` and `store_trajectory`",
                category=DeprecationWarning,
                stacklevel=1,
            )

        batch_mode = isinstance(structure, list)

        ase_results = [
            self._run_ase_safe(atoms, prev_dir=prev_dir)
            for atoms in (structure if batch_mode else [structure])
        ]

        task_docs = [
            ForceFieldTaskDocument.from_ase_compatible_result(
                self.ase_calculator_name,
                ase_result,
                self.steps,
                calculator_meta=self.calculator_meta,
                relax_kwargs=self.relax_kwargs,
                optimizer_kwargs=self.optimizer_kwargs,
                relax_cell=self.relax_cell,
                relax_shape=self.relax_shape,
                fix_symmetry=self.fix_symmetry,
                symprec=self.symprec if self.fix_symmetry else None,
                ionic_step_data=self.ionic_step_data,
                store_trajectory=self.store_trajectory,
                tags=self.tags,
                **self.task_document_kwargs,
            )
            for ase_result in ase_results
        ]
        return task_docs if batch_mode else task_docs[0]


@dataclass
class ForceFieldStaticMaker(ForceFieldRelaxMaker):

    name: str = "Force field static"
    force_field_name: str | MLFF | dict = MLFF.Forcefield
    relax_cell: bool = False
    relax_shape: bool = False
    steps: int = 1
    relax_kwargs: dict = field(default_factory=dict)
    optimizer_kwargs: dict = field(default_factory=dict)
    calculator_kwargs: dict = field(default_factory=dict)
    task_document_kwargs: dict = field(default_factory=dict)
