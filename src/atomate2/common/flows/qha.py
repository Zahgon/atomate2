
from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from jobflow import Flow, Maker

from atomate2.common.flows.eos import CommonEosMaker
from atomate2.common.jobs.qha import (
    analyze_free_energy,
    get_phonon_jobs,
    get_supercell_size,
)

if TYPE_CHECKING:
    from pathlib import Path

    from emmet.core.math import Matrix3D
    from pymatgen.core import Structure

    from atomate2.common.flows.phonons import BasePhononMaker
    from atomate2.forcefields.jobs import ForceFieldRelaxMaker
    from atomate2.vasp.jobs.core import BaseVaspMaker

supported_eos = frozenset(("vinet", "birch_murnaghan", "murnaghan"))


@dataclass
class CommonQhaMaker(Maker, ABC):

    name: str = "QHA Maker"
    initial_relax_maker: ForceFieldRelaxMaker | BaseVaspMaker | None = None
    eos_relax_maker: ForceFieldRelaxMaker | BaseVaspMaker | None = None
    phonon_maker: BasePhononMaker | None = None
    linear_strain: tuple[float, float] = (-0.05, 0.05)
    number_of_frames: int = 6
    t_max: float | None = None
    pressure: float | None = None
    ignore_imaginary_modes: bool = False
    skip_analysis: bool = False
    eos_type: Literal["vinet", "birch_murnaghan", "murnaghan"] = "vinet"
    analyze_free_energy_kwargs: dict = field(default_factory=dict)
    min_length: float | None = 20.0
    max_length: float | None = None
    prefer_90_degrees: bool = True
    allow_orthorhombic: bool = False
    get_supercell_size_kwargs: dict = field(default_factory=dict)

    def make(
        self,
        structure: Structure,
        supercell_matrix: Matrix3D | None = None,
        prev_dir: str | Path = None,
    ) -> Flow:
        """Run an EOS flow.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.
        supercell_matrix: list
            Instead of min_length, also a supercell_matrix can be given, e.g.
            [[1.0,0.0,0.0],[0.0,1.0,0.0],[0.0,0.0,1.0]
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from.

        Returns
        -------
        .Flow, a QHA flow
        """
        if self.eos_type not in supported_eos:
            raise ValueError(f"EOS not supported. Choose one of {set(supported_eos)}")

        qha_jobs = []

        self.eos = CommonEosMaker(
            initial_relax_maker=self.initial_relax_maker,
            eos_relax_maker=self.eos_relax_maker,
            static_maker=None,
            postprocessor=None,
            linear_strain=self.linear_strain,
            number_of_frames=self.number_of_frames,
        )

        eos_job = self.eos.make(structure)
        qha_jobs.append(eos_job)

        if supercell_matrix is None:
            supercell = get_supercell_size(
                eos_output=eos_job.output,
                min_length=self.min_length,
                max_length=self.max_length,
                prefer_90_degrees=self.prefer_90_degrees,
                allow_orthorhombic=self.allow_orthorhombic,
                **self.get_supercell_size_kwargs,
            )
            qha_jobs.append(supercell)
            supercell_matrix = supercell.output

        phonon_jobs = get_phonon_jobs(
            phonon_maker=self.phonon_maker,
            eos_output=eos_job.output,
            supercell_matrix=supercell_matrix,
        )
        qha_jobs.append(phonon_jobs)
        if not self.skip_analysis:
            analysis = analyze_free_energy(
                phonon_jobs.output,
                structure=structure,
                t_max=self.t_max,
                pressure=self.pressure,
                ignore_imaginary_modes=self.ignore_imaginary_modes,
                eos_type=self.eos_type,
                **self.analyze_free_energy_kwargs,
            )
            qha_jobs.append(analysis)

        return Flow(qha_jobs)

    def __post_init__(self) -> None:
        """Test settings during the initialisation."""
        if self.phonon_maker.bulk_relax_maker is not None:
            warnings.warn(
                "An additional bulk_relax_maker has been added "
                "to the phonon workflow. Please be aware "
                "that the volume needs to be kept fixed.",
                stacklevel=2,
            )
        if self.phonon_maker.static_energy_maker is None:
            warnings.warn(
                "A static energy maker "
                "is needed for "
                "this workflow."
                " Please add the static_energy_maker.",
                stacklevel=2,
            )

    @property
    @abstractmethod
    def prev_calc_dir_argname(self) -> str | None:
        """Name of argument informing static maker of previous calculation directory.

        As this differs between different DFT codes (e.g., VASP, CP2K), it
        has been left as a property to be implemented by the inheriting class.

        Note: this is only applicable if a relax_maker is specified; i.e., two
        calculations are performed for each ordering (relax -> static)
        """
