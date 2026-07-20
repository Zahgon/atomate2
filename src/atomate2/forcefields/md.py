
from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import TYPE_CHECKING

from jobflow import job

from atomate2.ase.md import AseMDMaker, MDEnsemble
from atomate2.forcefields.schemas import ForceFieldTaskDocument
from atomate2.forcefields.utils import _FORCEFIELD_DATA_OBJECTS, ForceFieldMixin

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core.structure import Molecule, Structure

    from atomate2.forcefields.schemas import ForceFieldMoleculeTaskDocument


@dataclass
class ForceFieldMDMaker(ForceFieldMixin, AseMDMaker):

    @job(
        data=[*_FORCEFIELD_DATA_OBJECTS, "ionic_steps"],
    )
    def make(
        self,
        structure: Molecule | Structure,
        prev_dir: str | Path | None = None,
    ) -> ForceFieldTaskDocument | ForceFieldMoleculeTaskDocument:
        """
        Perform MD on a structure using forcefields and jobflow.

        Parameters
        ----------
        structure: .Structure or Molecule
            pymatgen structure.
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
            added to match the method signature of other makers.
        """
        md_result = self._run_ase_safe(structure, prev_dir=prev_dir)

        self.task_document_kwargs = self.task_document_kwargs or {}
        if len(self.task_document_kwargs) > 0:
            warnings.warn(
                "`task_document_kwargs` is now deprecated, please use the top-level "
                "attributes `ionic_step_data` and `store_trajectory`",
                category=DeprecationWarning,
                stacklevel=1,
            )

        return ForceFieldTaskDocument.from_ase_compatible_result(
            self.ase_calculator_name,
            md_result,
            relax_cell=(self.ensemble == MDEnsemble.npt),
            relax_shape=False,
            steps=self.n_steps,
            calculator_meta=self.calculator_meta,
            relax_kwargs=None,
            optimizer_kwargs=None,
            fix_symmetry=False,
            symprec=None,
            ionic_step_data=self.ionic_step_data,
            store_trajectory=self.store_trajectory,
            tags=self.tags,
            **self.task_document_kwargs,
        )
