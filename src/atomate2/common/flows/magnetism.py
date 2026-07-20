
from __future__ import annotations

import warnings
from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from jobflow import Flow, Maker
from pymatgen.core import Element

from atomate2.common.jobs.magnetism import (
    enumerate_magnetic_orderings,
    postprocess_orderings,
    run_ordering_calculations,
)
from atomate2.vasp.jobs.core import RelaxMaker, StaticMaker
from atomate2.vasp.sets.core import StaticSetGenerator

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pymatgen.core.structure import Structure


__all__ = ["MagneticOrderingsMaker"]


@dataclass
class MagneticOrderingsMaker(Maker, ABC):

    name: str = "magnetic_orderings"
    static_maker: Maker = field(
        default_factory=lambda: StaticMaker(
            input_set_generator=StaticSetGenerator(user_incar_settings={"EDIFF": 1e-7})
        )
    )
    relax_maker: Maker | None = field(default_factory=RelaxMaker)
    default_magmoms: dict[Element, float] | None = None
    strategies: Sequence[
        Literal[
            "ferromagnetic",
            "antiferromagnetic",
            "antiferromagnetic_by_motif",
            "ferrimagnetic_by_motif",
            "ferrimagnetic_by_species",
            "nonmagnetic",
        ]
    ] = ("ferromagnetic", "antiferromagnetic")
    automatic: bool = True
    truncate_by_symmetry: bool = True
    transformation_kwargs: dict | None = None

    def __post_init__(self) -> None:
        """Ensure that the static and relax makers come from the same base maker.

        This ensures that the same DFT code is used for both calculations.
        """
        if self.relax_maker is None:
            warnings.warn(
                "No relax_maker provided, relaxations will be skipped. Please be"
                " sure that this is intended!",
                stacklevel=2,
            )
        else:
            static_base_maker_name = type(self.static_maker).__mro__[1].__name__
            relax_base_maker_name = type(self.relax_maker).__mro__[1].__name__
            if relax_base_maker_name != static_base_maker_name:
                warnings.warn(
                    "The provided static and relax makers do not use the "
                    "same DFT code! Please check the base maker used.",
                    stacklevel=2,
                )

    def make(
        self,
        structure: Structure,
    ) -> Flow:
        """Make a flow to calculate collinear magnetic orderings for a given structure.

        Parameters
        ----------
        structure : Structure
            A pymatgen structure object.

        Returns
        -------
        flow: Flow
            The magnetic ordering workflow.
        """
        jobs = []

        if Element("Co") in structure.elements:
            warnings.warn(
                (
                    "Co detected in structure! Please consider testing both low-spin"
                    " and high-spin configurations. The current default for Co (without"
                    " oxidation state) is high-spin. Refer to the defaults in"
                    " pymatgen/analysis/magnetism/default_magmoms.yaml for more"
                    " information. "
                ),
                stacklevel=2,
            )

        orderings = enumerate_magnetic_orderings(
            structure,
            default_magmoms=self.default_magmoms,
            strategies=self.strategies,
            automatic=self.automatic,
            truncate_by_symmetry=self.truncate_by_symmetry,
            transformation_kwargs=self.transformation_kwargs,
        )

        calculations = run_ordering_calculations(
            orderings.output,  # pylint: disable=no-member
            static_maker=self.static_maker,
            relax_maker=self.relax_maker,
        )

        postprocessing = postprocess_orderings(calculations.output)
        jobs = [orderings, calculations, postprocessing]

        return Flow(
            jobs=jobs,
            output=postprocessing.output,
            name=f"{self.name} ({structure.composition.reduced_formula})",
        )
