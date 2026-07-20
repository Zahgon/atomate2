
from __future__ import annotations

from io import StringIO

import openmm
from openmm import XmlSerializer
from openmm.app import Simulation
from openmm.app.pdbfile import PDBFile
from pydantic import BaseModel, Field


class OpenMMInterchange(BaseModel):

    system: str | None = Field(
        None, description="An XML file representing the OpenMM system."
    )
    state: str | None = Field(
        None,
        description="An XML file representing the OpenMM state.",
    )
    topology: str | None = Field(
        None,
        description="An XML file representing an OpenMM topology object."
        "This must correspond to the atom ordering in the system.",
    )

    def to_openmm_simulation(
        self,
        integrator: openmm.Integrator,
        platform: openmm.Platform,
        platformProperties: dict[str, str] | None = None,  # noqa: N803
    ) -> Simulation:
        """Create an OpenMM Simulation."""
        system = XmlSerializer.deserialize(self.system)
        state = XmlSerializer.deserialize(self.state)
        with StringIO(self.topology) as s:
            pdb = PDBFile(s)
            topology = pdb.getTopology()

        simulation = Simulation(
            topology,
            system,
            integrator,
            platform,
            platformProperties or {},
        )
        simulation.context.setState(state)
        return simulation
