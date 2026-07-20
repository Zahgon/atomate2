
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from emmet.core.types.enums import VaspObject
from jobflow import Flow, Maker

from atomate2.vasp.jobs.core import (
    HSEBSMaker,
    HSEStaticMaker,
    NonSCFMaker,
    RelaxMaker,
    StaticMaker,
)
from atomate2.vasp.sets.core import HSEBSSetGenerator, NonSCFSetGenerator

if TYPE_CHECKING:
    from pathlib import Path

    from jobflow import Job
    from pymatgen.core.structure import Structure
    from typing_extensions import Self

    from atomate2.vasp.jobs.base import BaseVaspMaker


@dataclass
class DoubleRelaxMaker(Maker):

    name: str = "double relax"
    relax_maker1: BaseVaspMaker | None = field(default_factory=RelaxMaker)
    relax_maker2: BaseVaspMaker = field(default_factory=RelaxMaker)

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Create a flow with two chained relaxations.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing two relaxations.
        """
        jobs: list[Job] = []
        if self.relax_maker1:
            relax1 = self.relax_maker1.make(structure, prev_dir=prev_dir)
            relax1.append_name(" 1")
            jobs += [relax1]
            structure = relax1.output.structure
            prev_dir = relax1.output.dir_name

        relax2 = self.relax_maker2.make(structure, prev_dir=prev_dir)
        relax2.append_name(" 2")
        jobs += [relax2]

        return Flow(jobs, output=relax2.output, name=self.name)

    @classmethod
    def from_relax_maker(cls, relax_maker: BaseVaspMaker) -> Self:
        """
        Instantiate the DoubleRelaxMaker with two relax makers of the same type.

        Parameters
        ----------
        relax_maker : .BaseVaspMaker
            Maker to use to generate the first and second relaxations.
        """
        return cls(
            relax_maker1=deepcopy(relax_maker), relax_maker2=deepcopy(relax_maker)
        )


@dataclass
class BandStructureMaker(Maker):

    name: str = "band structure"
    bandstructure_type: str = "both"
    static_maker: BaseVaspMaker = field(default_factory=StaticMaker)
    bs_maker: BaseVaspMaker = field(default_factory=NonSCFMaker)

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Create a band structure flow.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A band structure flow.
        """
        static_job = self.static_maker.make(structure, prev_dir=prev_dir)
        jobs = [static_job]

        outputs = {}
        bandstructure_type = self.bandstructure_type
        if bandstructure_type in ("both", "uniform"):
            uniform_job = self.bs_maker.make(
                static_job.output.structure,
                prev_dir=static_job.output.dir_name,
                mode="uniform",
            )
            uniform_job.name += " uniform"
            jobs.append(uniform_job)
            output = {
                "uniform": uniform_job.output,
                "uniform_bs": uniform_job.output.vasp_objects[VaspObject.BANDSTRUCTURE],
            }
            outputs.update(output)

        if bandstructure_type in ("both", "line"):
            line_job = self.bs_maker.make(
                static_job.output.structure,
                prev_dir=static_job.output.dir_name,
                mode="line",
            )
            line_job.name += " line"
            jobs.append(line_job)
            output = {
                "line": line_job.output,
                "line_bs": line_job.output.vasp_objects[VaspObject.BANDSTRUCTURE],
            }
            outputs.update(output)

        if bandstructure_type not in ("both", "line", "uniform"):
            raise ValueError(f"Unrecognised {bandstructure_type=}")

        return Flow(jobs, outputs, name=self.name)


@dataclass
class UniformBandStructureMaker(Maker):

    name: str = "uniform band structure"
    static_maker: BaseVaspMaker = field(default_factory=StaticMaker)
    bs_maker: BaseVaspMaker = field(default_factory=NonSCFMaker)

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Create a uniform band structure flow.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A uniform band structure flow.
        """
        static_job = self.static_maker.make(structure, prev_dir=prev_dir)
        uniform_job = self.bs_maker.make(
            static_job.output.structure,
            prev_dir=static_job.output.dir_name,
            mode="uniform",
        )
        uniform_job.name += " uniform"
        jobs = [static_job, uniform_job]
        return Flow(jobs, uniform_job.output, name=self.name)


@dataclass
class LineModeBandStructureMaker(Maker):

    name: str = "line band structure"
    static_maker: BaseVaspMaker = field(default_factory=StaticMaker)
    bs_maker: BaseVaspMaker = field(default_factory=NonSCFMaker)

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Create a line mode band structure flow.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A line mode band structure flow.
        """
        static_job = self.static_maker.make(structure, prev_dir=prev_dir)
        line_job = self.bs_maker.make(
            static_job.output.structure,
            prev_dir=static_job.output.dir_name,
            mode="line",
        )
        line_job.name += " line"
        jobs = [static_job, line_job]
        return Flow(jobs, line_job.output, name=self.name)


@dataclass
class HSEBandStructureMaker(BandStructureMaker):

    name: str = "hse band structure"
    bandstructure_type: str = "both"
    static_maker: BaseVaspMaker = field(default_factory=HSEStaticMaker)
    bs_maker: BaseVaspMaker = field(default_factory=HSEBSMaker)


@dataclass
class HSEUniformBandStructureMaker(UniformBandStructureMaker):

    name: str = "hse band structure"
    static_maker: BaseVaspMaker = field(default_factory=HSEStaticMaker)
    bs_maker: BaseVaspMaker = field(default_factory=HSEBSMaker)


@dataclass
class HSELineModeBandStructureMaker(LineModeBandStructureMaker):

    name: str = "hse band structure"
    static_maker: BaseVaspMaker = field(default_factory=HSEStaticMaker)
    bs_maker: BaseVaspMaker = field(default_factory=HSEBSMaker)


@dataclass
class RelaxBandStructureMaker(Maker):

    name: str = "relax and band structure"
    relax_maker: BaseVaspMaker = field(default_factory=DoubleRelaxMaker)
    band_structure_maker: BaseVaspMaker = field(default_factory=BandStructureMaker)

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Run a relaxation, then calculate the uniform and line mode band structures.

        Parameters
        ----------
        structure: .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A relax and band structure flow.
        """
        relax_job = self.relax_maker.make(structure, prev_dir=prev_dir)
        bs_flow = self.band_structure_maker.make(
            relax_job.output.structure, prev_dir=relax_job.output.dir_name
        )

        return Flow([relax_job, bs_flow], bs_flow.output, name=self.name)


@dataclass
class OpticsMaker(Maker):

    name: str = "static and optics"
    static_maker: BaseVaspMaker = field(default_factory=StaticMaker)
    band_structure_maker: BaseVaspMaker = field(
        default_factory=lambda: NonSCFMaker(
            name="optics",
            input_set_generator=NonSCFSetGenerator(optics=True),
        )
    )

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Run a static and then a non-scf optics calculation.

        Parameters
        ----------
        structure: .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A static and nscf with optics flow.
        """
        static_job = self.static_maker.make(structure, prev_dir=prev_dir)
        nscf_job = self.band_structure_maker.make(
            static_job.output.structure, prev_dir=static_job.output.dir_name
        )
        return Flow([static_job, nscf_job], nscf_job.output, name=self.name)


@dataclass
class HSEOpticsMaker(Maker):

    name: str = "hse static and optics"
    static_maker: BaseVaspMaker = field(default_factory=HSEStaticMaker)
    band_structure_maker: BaseVaspMaker = field(
        default_factory=lambda: HSEBSMaker(
            name="hse optics",
            input_set_generator=HSEBSSetGenerator(optics=True, mode="uniform"),
        )
    )

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Run a static and then a non-scf optics calculation.

        Parameters
        ----------
        structure: .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A static and nscf with optics flow.
        """
        static_job = self.static_maker.make(structure, prev_dir=prev_dir)
        bs_job = self.band_structure_maker.make(
            static_job.output.structure, prev_dir=static_job.output.dir_name
        )
        return Flow([static_job, bs_job], bs_job.output, name=self.name)
