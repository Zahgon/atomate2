
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from atomate2.aims.flows.core import DoubleRelaxMaker
from atomate2.aims.jobs.core import RelaxMaker
from atomate2.common.flows.eos import CommonEosMaker

if TYPE_CHECKING:
    from jobflow import Maker


@dataclass
class AimsEosMaker(CommonEosMaker):

    name: str = "aims eos"
    initial_relax_maker: Maker | None = field(
        default_factory=lambda: DoubleRelaxMaker.from_parameters({})
    )
    eos_relax_maker: Maker | None = field(
        default_factory=lambda: RelaxMaker.fixed_cell_relaxation(
            user_params={"species_dir": "tight"}
        )
    )

    @classmethod
    def from_parameters(cls, parameters: dict[str, Any], **kwargs) -> AimsEosMaker:
        """Creation of AimsEosMaker from parameters.

        Parameters
        ----------
        parameters : dict
            Dictionary of common parameters for both makers. The one exception is
            `species_dir` which can be either a string or a dict with keys [`initial`,
            `eos`]. If a string is given, it will be interpreted as the `species_dir`
            for the `eos` Maker; the initial double relaxation will be done then with
            the default `light` and `tight` species' defaults.
        kwargs
            Keyword arguments passed to `CommonEosMaker`.
        """
        species_dir = parameters.setdefault("species_dir", "tight")
        initial_params = parameters.copy()
        eos_params = parameters.copy()
        if isinstance(species_dir, dict):
            initial_params["species_dir"] = species_dir.get("initial")
            eos_params["species_dir"] = species_dir.get("eos", "tight")
        return cls(
            initial_relax_maker=DoubleRelaxMaker.from_parameters(initial_params),
            eos_relax_maker=RelaxMaker.fixed_cell_relaxation(user_params=eos_params),
            **kwargs,
        )
