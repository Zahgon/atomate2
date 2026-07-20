
from __future__ import annotations

import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Flow, Maker

from atomate2 import SETTINGS
from atomate2.common.jobs.gruneisen import (
    compute_gruneisen_param,
    run_phonon_jobs,
    shrink_expand_structure,
)

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core.structure import Structure

    from atomate2.aims.jobs.base import BaseAimsMaker
    from atomate2.common.flows.phonons import BasePhononMaker
    from atomate2.forcefields.jobs import ForceFieldRelaxMaker
    from atomate2.vasp.jobs.base import BaseVaspMaker


@dataclass
class BaseGruneisenMaker(Maker, ABC):

    name: str = "Gruneisen"
    bulk_relax_maker: ForceFieldRelaxMaker | BaseVaspMaker | BaseAimsMaker | None = None
    code: str = None
    const_vol_relax_maker: ForceFieldRelaxMaker | BaseVaspMaker | BaseAimsMaker = None
    kpath_scheme: str = "seekpath"
    phonon_maker: BasePhononMaker = None
    perc_vol: float = 0.01
    mesh: tuple[float, float, float] | float = 7_000
    compute_gruneisen_param_kwargs: dict = field(default_factory=dict)
    symprec: float = SETTINGS.PHONON_SYMPREC

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """
        Optimizes structure and runs phonon computations.

        Phonon computations are run for ground state, expanded and shrunk
        volume structures. Then, Grueneisen parameters are computed from
        this three phonon runs.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object. Please start with a structure
            that is nearly fully optimized as the internal optimizers
            have very strict settings!
        prev_dir : str or Path or None
            A previous calculation directory to use for copying outputs.
        """
        jobs = []  # initialize an empty list for jobs to be run

        opt_struct = dict.fromkeys(("ground", "plus", "minus"), None)
        prev_dir_dict = dict.fromkeys(("ground", "plus", "minus"), None)
        if (
            self.bulk_relax_maker is not None
        ):  # Optional job to relax the initial structure
            bulk_kwargs = {}
            if self.prev_calc_dir_argname is not None:
                bulk_kwargs[self.prev_calc_dir_argname] = prev_dir
            bulk = self.bulk_relax_maker.make(structure, **bulk_kwargs)
            jobs.append(bulk)
            opt_struct["ground"] = bulk.output.structure
            prev_dir = bulk.output.dir_name
            prev_dir_dict["ground"] = bulk.output.dir_name
        else:
            opt_struct["ground"] = structure
            prev_dir_dict["ground"] = prev_dir

        struct_dict = shrink_expand_structure(
            structure=bulk.output.structure, perc_vol=self.perc_vol
        )
        jobs.append(struct_dict)
        const_vol_relax_maker_kwargs = {}
        if self.prev_calc_dir_argname is not None:
            const_vol_relax_maker_kwargs[self.prev_calc_dir_argname] = prev_dir

        const_vol_struct_plus = self.const_vol_relax_maker.make(
            structure=struct_dict.output["plus"], **const_vol_relax_maker_kwargs
        )
        const_vol_struct_plus.append_name(" plus")
        jobs.append(const_vol_struct_plus)

        opt_struct["plus"] = (
            const_vol_struct_plus.output.structure
        )  # store opt struct of expanded volume

        const_vol_struct_minus = self.const_vol_relax_maker.make(
            structure=struct_dict.output["minus"], **const_vol_relax_maker_kwargs
        )
        const_vol_struct_minus.append_name(" minus")
        jobs.append(const_vol_struct_minus)

        opt_struct["minus"] = (
            const_vol_struct_minus.output.structure
        )  # store opt struct of expanded volume
        prev_dir_dict["plus"] = const_vol_struct_plus.output.dir_name
        prev_dir_dict["minus"] = const_vol_struct_minus.output.dir_name
        phonon_jobs = run_phonon_jobs(
            opt_struct,
            self.phonon_maker,
            symprec=self.symprec,
            prev_calc_dir_argname=self.prev_calc_dir_argname,
            prev_dir_dict=prev_dir_dict,
        )
        jobs.append(phonon_jobs)

        get_gru = compute_gruneisen_param(
            code=self.code,
            kpath_scheme=self.kpath_scheme,
            mesh=self.mesh,
            phonopy_yaml_paths_dict=phonon_jobs.output["phonon_yaml"],
            structure=opt_struct["ground"],
            symprec=self.symprec,
            phonon_imaginary_modes_info=phonon_jobs.output["imaginary_modes"],
            **self.compute_gruneisen_param_kwargs,
        )

        jobs.append(get_gru)

        return Flow(jobs, output=get_gru.output)

    @property
    @abstractmethod
    def prev_calc_dir_argname(self) -> str | None:
        """Name of argument informing static maker of previous calculation directory.

        As this differs between different DFT codes (e.g., VASP, CP2K), it
        has been left as a property to be implemented by the inheriting class.

        Note: this is only applicable if a relax_maker is specified; i.e., two
        calculations are performed for each ordering (relax -> static)
        """

    def __post_init__(self) -> None:
        """Test settings during the initialization."""
        if self.phonon_maker.bulk_relax_maker is not None:
            warnings.warn(
                "An additional bulk_relax_maker has been added "
                "to the phonon workflow. Please be aware "
                "that the volume needs to be kept fixed.",
                stacklevel=2,
            )
        if self.phonon_maker.symprec != self.symprec:
            warnings.warn(
                "You are using different symmetry precisions "
                "in the phonon makers and other parts of the "
                "Grüneisen workflow.",
                stacklevel=2,
            )
        if self.phonon_maker.static_energy_maker is not None:
            warnings.warn(
                "The static energy maker is not needed for this workflow.",
                stacklevel=2,
            )
