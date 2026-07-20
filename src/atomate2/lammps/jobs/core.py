
from dataclasses import dataclass, field
from pathlib import Path

from pymatgen.io.lammps.inputs import LammpsInputFile

from atomate2.lammps.jobs.base import BaseLammpsMaker
from atomate2.lammps.sets.core import (
    BaseLammpsSetGenerator,
    LammpsMinimizeSet,
    LammpsNPTSet,
    LammpsNVESet,
    LammpsNVTSet,
)


@dataclass
class LammpsNVTMaker(BaseLammpsMaker):

    name: str = "nvt"
    input_set_generator: BaseLammpsSetGenerator = field(default_factory=LammpsNVTSet)


@dataclass
class LammpsNPTMaker(BaseLammpsMaker):

    name: str = "npt"
    input_set_generator: BaseLammpsSetGenerator = field(default_factory=LammpsNPTSet)


@dataclass
class LammpsNVEMaker(BaseLammpsMaker):

    name: str = "nve"
    input_set_generator: BaseLammpsSetGenerator = field(default_factory=LammpsNVESet)


@dataclass
class MinimizationMaker(BaseLammpsMaker):

    name: str = "minimization"
    input_set_generator: BaseLammpsSetGenerator = field(
        default_factory=LammpsMinimizeSet
    )


@dataclass
class LammpsNPzATMaker(BaseLammpsMaker):

    name: str = "npzat"
    input_set_generator: BaseLammpsSetGenerator = field(
        default_factory=lambda: LammpsNPTSet(settings={"psymm": "z"})
    )


@dataclass
class CustomLammpsMaker(BaseLammpsMaker):

    name: str = "custom_lammps_job"
    inputfile: str | LammpsInputFile | Path = field(default=None)
    settings: dict = field(default_factory=dict)
    keep_stages: bool = field(default=True)
    include_defaults: bool = field(default=False)
    validate_params: bool = field(default=True)

    def __post_init__(self) -> None:
        """Initialize the input set generator for the custom LAMMPS job."""
        if not self.inputfile:
            raise ValueError(
                "Input file not specified. "
                "Use this maker only if you have a custom LAMMPS input file!"
            )

        self.input_set_generator = BaseLammpsSetGenerator(
            inputfile=self.inputfile,
            include_defaults=self.include_defaults,
            settings=self.settings,
            validate_params=False,
            force_field=self.force_field,
        )
