
from __future__ import annotations

from io import StringIO
from typing import TYPE_CHECKING, Annotated

import pandas as pd
from MDAnalysis import Universe
from MDAnalysis.analysis.dielectric import DielectricConstant
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    PlainValidator,
    WithJsonSchema,
)
from solvation_analysis.solute import Solute
from transport_analysis.viscosity import ViscosityHelfand

if TYPE_CHECKING:
    from typing import Any


def data_frame_validater(o: Any) -> pd.DataFrame:
    pass


def data_frame_serializer(df: pd.DataFrame) -> str:
    pass


DataFrame = Annotated[
    pd.DataFrame,
    PlainValidator(data_frame_validater),
    PlainSerializer(data_frame_serializer),
    WithJsonSchema({"type": "string"}),
]


class SolventBenchmarkingDoc(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    density: float | None = Field(None, description="Density of the solvent")

    viscosity_function_values: list[float] | None = Field(
        None, description="Viscosity function over time"
    )

    viscosity: float | None = Field(None, description="Viscosity of the solvent")

    dielectric: float | None = Field(
        None, description="Dielectric constant of the solvent"
    )

    job_uuid: str | None = Field(
        None, description="The UUID of the flow that generated this data."
    )

    flow_uuid: str | None = Field(
        None, description="The UUID of the top level host from that job."
    )

    dielectric_run_kwargs: dict | None = Field(
        None, description="kwargs passed to the DielectricConstant.run method"
    )

    viscosity_run_kwargs: dict | None = Field(
        None, description="kwargs passed to the ViscosityHelfand.run method"
    )

    tags: list[str] | None = Field(
        [], title="tag", description="Metadata tagged to the parent job."
    )

    @classmethod
    def from_universe(
        cls,
        u: Universe,
        temperature: float | None = None,
        density: float | None = None,
        job_uuid: str | None = None,
        flow_uuid: str | None = None,
        dielectric_run_kwargs: dict | None = None,
        viscosity_run_kwargs: dict | None = None,
        tags: list[str] | None = None,
    ) -> SolventBenchmarkingDoc:
        pass


class SolvationDoc(BaseModel):

    model_config = ConfigDict(arbitrary_types_allowed=True)

    solute_name: str | None = Field(None, description="Name of the solute")

    solvent_names: list[str] | None = Field(None, description="Names of the solvents")

    is_electrolyte: bool | None = Field(
        None, description="Whether system is an electrolyte"
    )


    coordination_numbers: dict[str, float] | None = Field(
        None,
        description="A dictionary where keys are residue names and values are "
        "the mean coordination number of that residue.",
    )


    coordinating_atoms: DataFrame | None = Field(
        None,
        description="Fraction of each atom_type participating in solvation, "
        "calculated for each solvent.",
    )

    coordination_vs_random: dict[str, float] | None = Field(
        None,
        description="Coordination number relative to random coordination.",
    )



    network_sizes: DataFrame | None = Field(
        None,
        description="Sizes of all networks, indexed by frame. Column headers are "
        "network sizes, e.g. the integer number of solutes + solvents in the network."
        "The values in each column are the number of networks with that size in each "
        "frame.",
    )

    solute_status: dict[str, float] | None = Field(
        None,
        description="A dictionary where the keys are the “status” of the "
        "solute and the values are the fraction of solute with that "
        "status, averaged over all frames. “isolated” means that the solute not "
        "coordinated with any of the networking solvents, network size is 1. "
        "“paired” means the solute and is coordinated with a single networking "
        "solvent and that solvent is not coordinated to any other solutes, "
        "network size is 2. “networked” means that the solute is coordinated to "
        "more than one solvent or its solvent is coordinated to more than one "
        "solute, network size >= 3.",
    )



    solvent_pairing: dict[str, float] | None = Field(
        None, description="Fraction of each solvent coordinated to the solute."
    )


    fraction_free_solvents: dict[str, float] | None = Field(
        None, description="Fraction of each solvent not coordinated to solute."
    )

    diluent_composition: dict[str, float] | None = Field(
        None, description="Fraction of diluent constituted by each solvent."
    )


    diluent_counts: DataFrame | None = Field(
        None, description="Solvent counts in each frame."
    )


    residence_times: dict[str, float] | None = Field(
        None,
        description="Average residence time of each solvent."
        "Calculated by 1/e cutoff on autocovariance function.",
    )

    residence_times_fit: dict[str, float] | None = Field(
        None,
        description="Average residence time of each solvent."
        "Calculated by fitting the autocovariance function to an exponential decay.",
    )


    speciation_fraction: DataFrame | None = Field(
        None, description="Fraction of shells of each type."
    )

    solvent_co_occurrence: DataFrame | None = Field(
        None,
        description="The actual co-occurrence of solvents divided by "
        "the expected co-occurrence in randomly distributed solvation shells."
        "i.e. given a molecule of solvent i in the shell, the probability of "
        "solvent j's presence relative to choosing a solvent at random "
        "from the pool of all coordinated solvents. ",
    )

    job_uuid: str | None = Field(
        None, description="The UUID of the flow that generated this data."
    )

    flow_uuid: str | None = Field(
        None, description="The UUID of the top level host from that job."
    )

    @classmethod
    def from_solute(
        cls,
        solute: Solute,
        job_uuid: str | None = None,
        flow_uuid: str | None = None,
    ) -> SolvationDoc:
        pass
