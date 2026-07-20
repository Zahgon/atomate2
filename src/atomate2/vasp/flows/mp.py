
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Flow, Maker

try:
    from pymatgen.io.vasp.sets import LobsterSet  # type: ignore[attr-defined]
except ImportError:
    from pymatgen.io.lobster.sets import LobsterSet  # type: ignore[attr-defined]

from atomate2.common.jobs.utils import remove_workflow_files
from atomate2.common.utils import _recursive_get_dir_names
from atomate2.lobster.jobs import LobsterMaker
from atomate2.vasp.flows.core import DoubleRelaxMaker
from atomate2.vasp.flows.lobster import VaspLobsterMaker
from atomate2.vasp.jobs.mp import (
    MP24PreRelaxMaker,
    MP24RelaxMaker,
    MP24StaticMaker,
    MPGGARelaxMaker,
    MPGGAStaticMaker,
    MPMetaGGARelaxMaker,
    MPMetaGGAStaticMaker,
    MPPreRelaxMaker,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pymatgen.core.structure import Structure

    from atomate2.vasp.jobs.base import BaseVaspMaker


@dataclass
class MPGGADoubleRelaxMaker(DoubleRelaxMaker):

    name: str = "MP GGA double relax"
    relax_maker1: Maker | None = field(default_factory=MPGGARelaxMaker)
    relax_maker2: Maker = field(
        default_factory=lambda: MPGGARelaxMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR", "CHGCAR")}
        )
    )


@dataclass
class MPMetaGGADoubleRelaxMaker(DoubleRelaxMaker):

    name: str = "MP meta-GGA double relax"
    relax_maker1: Maker | None = field(default_factory=MPPreRelaxMaker)
    relax_maker2: Maker = field(
        default_factory=lambda: MPMetaGGARelaxMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR", "CHGCAR")}
        )
    )


@dataclass
class MPGGADoubleRelaxStaticMaker(Maker):

    name: str = "MP GGA relax"
    relax_maker: Maker = field(default_factory=MPGGADoubleRelaxMaker)
    static_maker: Maker | None = field(
        default_factory=lambda: MPGGAStaticMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR", "CHGCAR")}
        )
    )

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """
        1, 2 or 3-step flow with optional pre-relax and final static jobs.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing the MP relaxation workflow.
        """
        relax_flow = self.relax_maker.make(structure=structure, prev_dir=prev_dir)
        output = relax_flow.output
        jobs = [relax_flow]

        if self.static_maker:
            static_job = self.static_maker.make(
                structure=output.structure, prev_dir=output.dir_name
            )
            output = static_job.output
            jobs += [static_job]

        return Flow(jobs=jobs, output=output, name=self.name)


@dataclass
class MPMetaGGADoubleRelaxStaticMaker(MPGGADoubleRelaxMaker):

    name: str = "MP meta-GGA relax"
    relax_maker: Maker = field(default_factory=MPMetaGGADoubleRelaxMaker)
    static_maker: Maker | None = field(
        default_factory=lambda: MPMetaGGAStaticMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR", "CHGCAR")}
        )
    )

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Make a 2-step flow with a cheap pre-relaxation, then a high-quality one.

        An optional static calculation can be performed before the relaxation.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing the MP relaxation workflow.
        """
        relax_flow = self.relax_maker.make(structure=structure, prev_dir=prev_dir)
        output = relax_flow.output
        jobs = [relax_flow]
        if self.static_maker:
            static_job = self.static_maker.make(
                structure=output.structure, prev_dir=output.dir_name
            )
            output = static_job.output
            jobs += [static_job]

        return Flow(jobs=jobs, output=output, name=self.name)


@dataclass
class MP24DoubleRelaxMaker(DoubleRelaxMaker):

    name: str = "MP24 double relax"
    relax_maker1: Maker | None = field(default_factory=MP24PreRelaxMaker)
    relax_maker2: Maker = field(
        default_factory=lambda: MP24RelaxMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR", "CHGCAR")}
        )
    )


@dataclass
class MP24DoubleRelaxStaticMaker(Maker):

    name: str = "MP24 r2SCAN workflow"
    relax_maker: Maker = field(default_factory=MP24DoubleRelaxMaker)
    static_maker: Maker = field(
        default_factory=lambda: MP24StaticMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR", "CHGCAR")}
        )
    )
    clean_files: Sequence[str] | None = ("WAVECAR",)

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Relax a structure with r2SCAN.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing the MP relaxation workflow.
        """
        relax_flow = self.relax_maker.make(structure=structure, prev_dir=prev_dir)

        static_job = self.static_maker.make(
            structure=relax_flow.output.structure, prev_dir=relax_flow.output.dir_name
        )

        jobs = [relax_flow, static_job]

        self.clean_files = self.clean_files or []
        if len(self.clean_files) > 0:
            directories: list[str] = []
            _recursive_get_dir_names(jobs, directories)
            cleanup = remove_workflow_files(
                directories=directories,
                file_names=self.clean_files,
                allow_zpath=True,
            )
            jobs += [cleanup]

        return Flow(jobs=jobs, output=static_job.output, name=self.name)


@dataclass
class MPVaspLobsterMaker(VaspLobsterMaker):

    name: str = "lobster"
    relax_maker: BaseVaspMaker | None = field(default_factory=MPGGADoubleRelaxMaker)
    lobster_static_maker: BaseVaspMaker = field(
        default_factory=lambda: MPGGAStaticMaker(input_set_generator=LobsterSet())
    )
    lobster_maker: LobsterMaker | None = field(default_factory=LobsterMaker)
    delete_wavecars: bool = True
    address_min_basis: str | None = None
    address_max_basis: str | None = None
