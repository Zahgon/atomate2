
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Flow, Maker, OnMissing

from atomate2 import SETTINGS
from atomate2.common.jobs.elastic import (
    fit_elastic_tensor,
    generate_elastic_deformations,
    run_elastic_deformations,
)
from atomate2.common.jobs.utils import structure_to_conventional

if TYPE_CHECKING:
    from pathlib import Path

    from emmet.core.math import Matrix3D
    from pymatgen.core.structure import Structure

    from atomate2.aims.jobs.base import BaseAimsMaker
    from atomate2.forcefields.jobs import ForceFieldRelaxMaker
    from atomate2.torchsim import TorchSimOptimizeMaker
    from atomate2.vasp.jobs.base import BaseVaspMaker


@dataclass
class BaseElasticMaker(Maker, ABC):

    name: str = "elastic"
    order: int = 2
    sym_reduce: bool = True
    symprec: float = SETTINGS.SYMPREC
    bulk_relax_maker: (
        BaseAimsMaker
        | BaseVaspMaker
        | ForceFieldRelaxMaker
        | TorchSimOptimizeMaker
        | None
    ) = None
    elastic_relax_maker: (
        BaseAimsMaker | BaseVaspMaker | ForceFieldRelaxMaker | TorchSimOptimizeMaker
    ) = None  # constant volume optimization
    max_failed_deformations: int | float | None = None
    generate_elastic_deformations_kwargs: dict = field(default_factory=dict)
    fit_elastic_tensor_kwargs: dict = field(default_factory=dict)
    task_document_kwargs: dict = field(default_factory=dict)
    socket: bool = False

    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
        equilibrium_stress: Matrix3D | None = None,
        conventional: bool = False,
    ) -> Flow:
        """
        Make flow to calculate the elastic constant.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure.
        prev_dir : str or Path or None
            A previous vasp calculation directory to use for copying outputs.
        equilibrium_stress : tuple of tuple of float
            The equilibrium stress of the (relaxed) structure, if known.
        conventional : bool
            Whether to transform the structure into the conventional cell.
        """
        jobs = []

        if self.bulk_relax_maker is not None:
            bulk_kwargs = {}
            if self.prev_calc_dir_argname is not None:
                bulk_kwargs[self.prev_calc_dir_argname] = prev_dir
            bulk = self.bulk_relax_maker.make(structure, **bulk_kwargs)
            jobs.append(bulk)
            structure = bulk.output.structure
            prev_dir = bulk.output.dir_name
            if equilibrium_stress is None:
                equilibrium_stress = bulk.output.output.stress

        if conventional:
            stc = structure_to_conventional(structure, self.symprec)
            jobs.append(stc)
            structure = stc.output

        deformations = generate_elastic_deformations(
            structure,
            order=self.order,
            sym_reduce=self.sym_reduce,
            symprec=self.symprec,
            **self.generate_elastic_deformations_kwargs,
        )

        deformation_calcs = run_elastic_deformations(
            structure,
            deformations.output,
            elastic_relax_maker=self.elastic_relax_maker,
            prev_dir=prev_dir,
            socket=self.socket,
        )
        fit_tensor = fit_elastic_tensor(
            structure,
            deformation_calcs.output,
            equilibrium_stress=equilibrium_stress,
            order=self.order,
            symprec=self.symprec if self.sym_reduce else None,
            stress_sign_factor=self.stress_sign_correction,
            max_failed_deformations=self.max_failed_deformations,
            **self.fit_elastic_tensor_kwargs,
            **self.task_document_kwargs,
        )

        fit_tensor.config.on_missing_references = OnMissing.NONE

        jobs += [deformations, deformation_calcs, fit_tensor]

        return Flow(
            jobs=jobs,
            output=fit_tensor.output,
            name=self.name,
        )

    @property
    def stress_sign_correction(self) -> float:
        pass

    @property
    @abstractmethod
    def prev_calc_dir_argname(self) -> str:
        """Name of argument informing static maker of previous calculation directory.

        As this differs between different DFT codes (e.g., VASP, CP2K), it
        has been left as a property to be implemented by the inheriting class.
        Note: this is only applicable if a relax_maker is specified; i.e., two
        calculations are performed for each ordering (relax -> static)
        """
