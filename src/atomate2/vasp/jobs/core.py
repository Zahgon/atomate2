
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from pymatgen.alchemy.materials import TransformedStructure
from pymatgen.alchemy.transmuters import StandardTransmuter

from atomate2.common.utils import get_transformations
from atomate2.vasp.jobs.base import BaseVaspMaker, vasp_job
from atomate2.vasp.sets.core import (
    HSEBSSetGenerator,
    HSERelaxSetGenerator,
    HSEStaticSetGenerator,
    HSETightRelaxSetGenerator,
    NonSCFSetGenerator,
    RelaxConstVolSetGenerator,
    RelaxSetGenerator,
    StaticSetGenerator,
    TightRelaxConstVolSetGenerator,
    TightRelaxSetGenerator,
)

if TYPE_CHECKING:
    from pathlib import Path

    from jobflow import Response
    from pymatgen.core.structure import Structure

    from atomate2.vasp.sets.base import VaspInputGenerator


logger = logging.getLogger(__name__)


@dataclass
class StaticMaker(BaseVaspMaker):

    name: str = "static"
    input_set_generator: VaspInputGenerator = field(default_factory=StaticSetGenerator)


@dataclass
class RelaxMaker(BaseVaspMaker):

    name: str = "relax"
    input_set_generator: VaspInputGenerator = field(default_factory=RelaxSetGenerator)


class RelaxConstVolMaker(BaseVaspMaker):

    name: str = "relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=RelaxConstVolSetGenerator
    )


@dataclass
class TightRelaxMaker(BaseVaspMaker):

    name: str = "tight relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=TightRelaxSetGenerator
    )


@dataclass
class TightRelaxConstVolMaker(BaseVaspMaker):

    name: str = "tight relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=TightRelaxConstVolSetGenerator
    )


@dataclass
class TightConstVolRelaxMaker(BaseVaspMaker):

    name: str = "tight relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=TightRelaxConstVolSetGenerator
    )


@dataclass
class NonSCFMaker(BaseVaspMaker):

    name: str = "non-scf"
    input_set_generator: VaspInputGenerator = field(default_factory=NonSCFSetGenerator)

    @vasp_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None,
        mode: str = "uniform",
    ) -> Response:
        """Run a non-scf VASP job.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.
        mode : str
            Type of band structure calculation. Options are:
            - "line": Full band structure along symmetry lines.
            - "uniform": Uniform mesh band structure.
        """
        self.input_set_generator.mode = mode

        self.task_document_kwargs.setdefault("parse_dos", mode == "uniform")
        self.task_document_kwargs.setdefault("parse_bandstructure", mode)
        self.copy_vasp_kwargs.setdefault("additional_vasp_files", ("CHGCAR",))

        return super().make.original(self, structure, prev_dir)


@dataclass
class HSERelaxMaker(BaseVaspMaker):

    name: str = "hse relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=HSERelaxSetGenerator
    )


@dataclass
class HSETightRelaxMaker(BaseVaspMaker):

    name: str = "hse tight relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=HSETightRelaxSetGenerator
    )


@dataclass
class HSEStaticMaker(BaseVaspMaker):

    name: str = "hse static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=HSEStaticSetGenerator
    )


@dataclass
class HSEBSMaker(BaseVaspMaker):

    name: str = "hse band structure"
    input_set_generator: VaspInputGenerator = field(default_factory=HSEBSSetGenerator)

    @vasp_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
        mode: Literal["line", "uniform", "gap"] = "uniform",
    ) -> Response:
        """Run an HSE06 band structure VASP job.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.
        mode : str = "uniform"
            Type of band structure calculation. Options are:
            - "line": Full band structure along symmetry lines.
            - "uniform": Uniform mesh band structure.
            - "gap": Get the energy at the CBM and VBM.
        """
        self.input_set_generator.mode = mode

        if mode == "gap" and prev_dir is None:
            logger.warning(
                "HSE band structure in 'gap' mode requires a previous VASP calculation "
                "directory from which to extract the VBM and CBM k-points. This "
                "calculation will instead be a standard uniform calculation."
            )
            mode = "uniform"

        self.task_document_kwargs.setdefault("parse_dos", "uniform" in mode)

        parse_bandstructure = "uniform" if mode == "gap" else mode
        self.task_document_kwargs.setdefault("parse_bandstructure", parse_bandstructure)

        if prev_dir is not None:
            self.copy_vasp_kwargs.setdefault("additional_vasp_files", ("CHGCAR",))

        return super().make.original(self, structure, prev_dir)


@dataclass
class DielectricMaker(BaseVaspMaker):

    name: str = "dielectric"
    input_set_generator: StaticSetGenerator = field(
        default_factory=lambda: StaticSetGenerator(lepsilon=True, auto_ispin=True)
    )


@dataclass
class PolarizationMaker(BaseVaspMaker):

    name: str = "polarization"
    input_set_generator: StaticSetGenerator = field(
        default_factory=lambda: StaticSetGenerator(lcalcpol=True, auto_ispin=True)
    )


@dataclass
class TransmuterMaker(BaseVaspMaker):

    name: str = "transmuter"
    transformations: tuple[str, ...] = field(default_factory=tuple)
    transformation_params: tuple[dict, ...] | None = None
    input_set_generator: VaspInputGenerator = field(default_factory=StaticSetGenerator)

    @vasp_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> Response:
        """Run a transmuter VASP job.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.
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
