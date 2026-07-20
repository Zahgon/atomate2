
from __future__ import annotations

import logging
import time
from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from emmet.core.types.enums import StoreTrajectoryOption
from jobflow import Maker, job
from pymatgen.core import Molecule, Structure
from pymatgen.io.ase import AseAtomsAdaptor
from pymatgen.util.due import Doi, due

from atomate2.ase.schemas import AseResult, AseTaskDoc
from atomate2.ase.utils import AseRelaxer

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pathlib import Path

    from ase.calculators.calculator import Calculator

    from atomate2.ase.schemas import AseMoleculeTaskDoc, AseStructureTaskDoc

_ASE_DATA_OBJECTS = ["trajectory"]


@due.dcite(
    Doi("10.1088/1361-648X/aa680e"), description="Atomic simulation environment."
)
@dataclass
class AseMaker(Maker, ABC):

    name: str = "ASE maker"
    calculator_kwargs: dict = field(default_factory=dict)
    ionic_step_data: tuple[str, ...] | None = (
        "energy",
        "forces",
        "magmoms",
        "stress",
        "mol_or_struct",
    )
    store_trajectory: StoreTrajectoryOption = StoreTrajectoryOption.NO
    tags: list[str] | None = None

    def __post_init__(self) -> None:
        """Enable caching of the ASE calculator via private attribute."""
        self._calculator: Calculator | None = None

    @job(data=_ASE_DATA_OBJECTS)
    def make(
        self,
        mol_or_struct: Molecule | Structure | list[Molecule | Structure],
        prev_dir: str | Path | None = None,
    ) -> (
        AseStructureTaskDoc
        | AseMoleculeTaskDoc
        | list[AseStructureTaskDoc | AseMoleculeTaskDoc]
    ):
        """
        Run ASE as job, can be re-implemented in subclasses.

        Parameters
        ----------
        mol_or_struct: .Molecule, .Structure, or a list thereof
            pymatgen molecule(s) or structure(s)
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
                added to match the method signature of other makers.

        Returns
        -------
        AseStructureTaskDoc, AseMoleculeTaskDoc, or list thereof.
        """
        batch_mode = isinstance(mol_or_struct, list)
        results = [
            AseTaskDoc.to_mol_or_struct_metadata_doc(
                getattr(self.calculator, "name", type(self.calculator).__name__),
                self.run_ase(atoms, prev_dir=prev_dir),
            )
            for atoms in (mol_or_struct if batch_mode else [mol_or_struct])
        ]
        return results if batch_mode else results[0]

    def run_ase(
        self,
        mol_or_struct: Structure | Molecule,
        prev_dir: str | Path | None = None,
    ) -> AseResult:
        """
        Run ASE, can be re-implemented in subclasses.

        Parameters
        ----------
        mol_or_struct: .Molecule or .Structure
            pymatgen molecule or structure
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
                added to match the method signature of other makers.
        """
        is_mol = isinstance(mol_or_struct, Molecule)
        adaptor = AseAtomsAdaptor()
        atoms = adaptor.get_atoms(mol_or_struct)
        atoms.calc = self.calculator
        t_i = time.perf_counter()
        final_energy = atoms.get_potential_energy()
        t_f = time.perf_counter()
        return AseResult(
            final_mol_or_struct=getattr(
                adaptor, f"get_{'molecule' if is_mol else 'structure'}"
            )(atoms),
            final_energy=final_energy,
            elapsed_time=t_f - t_i,
        )

    def _get_calculator(self) -> Calculator:
        """Load ASE calculator, to be implemented by the user.

        NB: To avoid breaking behavior, this method by default
        does nothing and *should not* be an `abstractmethod`.

        Previously, users would define the `calculator` attr
        directly. That is still possible but will not benefit
        from caching the calculator.
        """

    @property
    def calculator(self) -> Calculator:
        pass


@dataclass
class AseRelaxMaker(AseMaker):

    name: str = "ASE relaxation"
    relax_cell: bool = True
    relax_shape: bool = False
    fix_symmetry: bool = False
    symprec: float | None = 1e-2
    steps: int = 500
    relax_kwargs: dict = field(default_factory=dict)
    optimizer_kwargs: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure that physical relaxation settings are used."""
        super().__post_init__()
        if self.relax_cell and self.relax_shape:
            raise ValueError(
                "You have set both `relax_cell` (relaxing the cell shape and volume) "
                "and `relax_shape` (relaxing only the cell shape at fixed volume) "
                "to be `True`. Select at most one option to be `True`."
            )

    @job(data=_ASE_DATA_OBJECTS)
    def make(
        self,
        mol_or_struct: Molecule | Structure | list[Molecule | Structure],
        prev_dir: str | Path | None = None,
    ) -> (
        AseStructureTaskDoc
        | AseMoleculeTaskDoc
        | list[AseStructureTaskDoc | AseMoleculeTaskDoc]
    ):
        """
        Relax a structure or molecule using ASE as a job.

        Parameters
        ----------
        mol_or_struct: .Molecule or .Structure, or list thereof
            pymatgen molecule(s) or structure(s)
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
                added to match the method signature of other makers.

        Returns
        -------
        AseStructureTaskDoc or AseMoleculeTaskDoc, or list thereof
        """
        batch_mode = isinstance(mol_or_struct, list)

        results = [
            AseTaskDoc.to_mol_or_struct_metadata_doc(
                getattr(self.calculator, "name", type(self.calculator).__name__),
                self.run_ase(atoms, prev_dir=prev_dir),
                self.steps,
                relax_kwargs=self.relax_kwargs,
                optimizer_kwargs=self.optimizer_kwargs,
                relax_cell=self.relax_cell,
                relax_shape=self.relax_shape,
                fix_symmetry=self.fix_symmetry,
                symprec=self.symprec if self.fix_symmetry else None,
                ionic_step_data=self.ionic_step_data,
                store_trajectory=self.store_trajectory,
                tags=self.tags,
            )
            for atoms in (mol_or_struct if batch_mode else [mol_or_struct])
        ]
        return results if batch_mode else results[0]

    def run_ase(
        self,
        mol_or_struct: Structure | Molecule,
        prev_dir: str | Path | None = None,
    ) -> AseResult:
        """
        Relax a structure or molecule using ASE, not as a job.

        Parameters
        ----------
        mol_or_struct: .Molecule or .Structure
            pymatgen molecule or structure
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
                added to match the method signature of other makers.
        """
        if self.steps < 0:
            logger.warning(
                "WARNING: A negative number of steps is not possible. "
                "Defaulting to a static calculation."
            )

        relaxer = AseRelaxer(
            self.calculator,
            relax_cell=self.relax_cell,
            relax_shape=self.relax_shape,
            fix_symmetry=self.fix_symmetry,
            symprec=self.symprec,
            **self.optimizer_kwargs,
        )
        return relaxer.relax(mol_or_struct, steps=self.steps, **self.relax_kwargs)


@dataclass
class EmtRelaxMaker(AseRelaxMaker):

    name: str = "EMT relaxation"

    def _get_calculator(self) -> Calculator:
        pass


@dataclass
class LennardJonesRelaxMaker(AseRelaxMaker):

    name: str = "Lennard-Jones 6-12 relaxation"

    def _get_calculator(self) -> None:
        pass


@dataclass
class LennardJonesStaticMaker(LennardJonesRelaxMaker):

    name: str = "Lennard-Jones 6-12 static"
    steps: int = 1


@dataclass
class GFNxTBRelaxMaker(AseRelaxMaker):

    name: str = "GFN-xTB relaxation"
    calculator_kwargs: dict = field(
        default_factory=lambda: {
            "method": "GFN1-xTB",
            "charge": None,
            "multiplicity": None,
            "accuracy": 1.0,
            "guess": "sad",
            "max_iterations": 250,
            "mixer_damping": 0.4,
            "electric_field": None,
            "spin_polarization": None,
            "electronic_temperature": 300.0,
            "cache_api": True,
            "verbosity": 1,
        }
    )

    def _get_calculator(self) -> None:
        pass


@dataclass
class GFNxTBStaticMaker(GFNxTBRelaxMaker):

    name: str = "GFN-xTB static"
    steps: int = 1
