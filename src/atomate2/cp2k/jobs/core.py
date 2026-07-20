
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from custodian.cp2k.handlers import (
    AbortHandler,
    FrozenJobErrorHandler,
    NumericalPrecisionHandler,
    StdErrHandler,
    WalltimeHandler,
)
from pymatgen.alchemy.materials import TransformedStructure
from pymatgen.alchemy.transmuters import StandardTransmuter

from atomate2.common.utils import get_transformations
from atomate2.cp2k.jobs.base import BaseCp2kMaker, cp2k_job
from atomate2.cp2k.sets.core import (
    CellOptSetGenerator,
    HybridCellOptSetGenerator,
    HybridRelaxSetGenerator,
    HybridStaticSetGenerator,
    MDSetGenerator,
    NonSCFSetGenerator,
    RelaxSetGenerator,
    StaticSetGenerator,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core.structure import Structure

    from atomate2.cp2k.sets.base import Cp2kInputGenerator


logger = logging.getLogger(__name__)


@dataclass
class StaticMaker(BaseCp2kMaker):

    name: str = "static"
    input_set_generator: Cp2kInputGenerator = field(default_factory=StaticSetGenerator)


@dataclass
class RelaxMaker(BaseCp2kMaker):

    name: str = "relax"
    input_set_generator: Cp2kInputGenerator = field(default_factory=RelaxSetGenerator)


@dataclass
class CellOptMaker(BaseCp2kMaker):

    name: str = "relax"
    input_set_generator: Cp2kInputGenerator = field(default_factory=CellOptSetGenerator)


@dataclass
class HybridStaticMaker(BaseCp2kMaker):

    name: str = "hybrid static"
    input_set_generator: Cp2kInputGenerator = field(
        default_factory=HybridStaticSetGenerator
    )


@dataclass
class HybridRelaxMaker(BaseCp2kMaker):

    name: str = "hybrid relax"
    input_set_generator: Cp2kInputGenerator = field(
        default_factory=HybridRelaxSetGenerator
    )


@dataclass
class HybridCellOptMaker(BaseCp2kMaker):

    name: str = "hybrid cell opt"
    input_set_generator: Cp2kInputGenerator = field(
        default_factory=HybridCellOptSetGenerator
    )


@dataclass
class NonSCFMaker(BaseCp2kMaker):

    name: str = "non-scf"
    input_set_generator: Cp2kInputGenerator = field(default_factory=NonSCFSetGenerator)

    run_cp2k_kwargs: dict = field(
        default_factory=lambda: {
            "handlers": (
                StdErrHandler(),
                FrozenJobErrorHandler(),
                AbortHandler(),
                NumericalPrecisionHandler(),
                WalltimeHandler(),
            ),
            "validators": (),
        }
    )

    @cp2k_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None,
        mode: str = "uniform",
    ) -> None:
        """Run a non-scf CP2K job.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous CP2K calculation directory to copy output files from.
        mode : str
            Type of band structure calculation. Options are:
            - "line": Full band structure along symmetry lines.
            - "uniform": Uniform mesh band structure.
        """
        self.input_set_generator.mode = mode

        self.task_document_kwargs.setdefault("parse_dos", mode == "uniform")
        self.task_document_kwargs.setdefault("parse_bandstructure", mode)
        self.copy_cp2k_kwargs.setdefault("additional_cp2k_files", ("wfn",))

        return super().make.original(self, structure, prev_dir)


@dataclass
class TransmuterMaker(BaseCp2kMaker):

    name: str = "transmuter"
    transformations: tuple[str, ...] = field(default_factory=tuple)
    transformation_params: tuple[dict, ...] | None = None
    input_set_generator: Cp2kInputGenerator = field(default_factory=StaticSetGenerator)

    @cp2k_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> None:
        """Run a transmuter Cp2k job.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous Cp2k calculation directory to copy output files from.
        """
        transformations = get_transformations(
            self.transformations, self.transformation_params
        )
        ts = TransformedStructure(structure)
        transmuter = StandardTransmuter([ts], transformations)
        structure = transmuter.transformed_structures[-1].final_structure

        tjson = transmuter.transformed_structures[-1]
        self.write_additional_data.setdefault("transformations:json", tjson)

        return super().make.original(self, structure, prev_dir)


@dataclass
class MDMaker(BaseCp2kMaker):

    name: str = "md"
    input_set_generator: Cp2kInputGenerator = field(default_factory=MDSetGenerator)
    task_document_kwargs: dict = field(
        default_factory=lambda: {"store_trajectory": True}
    )
