
from pydantic import BaseModel, Field
from pymatgen.core import Structure


class AdsorptionDocument(BaseModel):

    structures: list[Structure] = Field(
        ..., description="List of adsorption structures."
    )

    configuration_numbers: list[int] = Field(
        ..., description="List of configuration numbers for the adsorption structures."
    )

    adsorption_energies: list[float] = Field(
        ..., description="List of adsorption energies corresponding to each structure."
    )

    job_dirs: list[str] = Field(
        ..., description="List of directories where the adsorption jobs were run."
    )

    @classmethod
    def from_adsorption(
        cls,
        structures: list[Structure],
        configuration_numbers: list[int],
        adsorption_energies: list[float],
        job_dirs: list[str],
    ) -> "AdsorptionDocument":
        pass
