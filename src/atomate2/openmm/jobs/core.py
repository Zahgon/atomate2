
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
from openmm import Integrator, LangevinMiddleIntegrator, MonteCarloBarostat
from openmm.app import StateDataReporter
from openmm.unit import atmosphere, kelvin, kilojoules_per_mole, nanometer, picoseconds

from atomate2.openmm.jobs.base import BaseOpenMMMaker
from atomate2.openmm.utils import create_list_summing_to

if TYPE_CHECKING:
    from pathlib import Path

    from emmet.core.openmm import OpenMMTaskDocument
    from openmm.app import Simulation


@dataclass
class EnergyMinimizationMaker(BaseOpenMMMaker):

    name: str = "energy minimization"
    n_steps: int = 0
    tolerance: float = 10
    max_iterations: int = 0

    def run_openmm(self, sim: Simulation, dir_name: Path) -> None:
        """Run the energy minimization with OpenMM.

        This method performs energy minimization on the molecular system using
        the OpenMM simulation package. It minimizes the energy of the system
        based on the specified tolerance and maximum number of iterations.

        Parameters
        ----------
        sim : Simulation
            The OpenMM simulation object.
        """
        if self.n_steps != 0:
            raise ValueError("Energy minimization should have 0 steps.")

        sim.minimizeEnergy(
            tolerance=self.tolerance * kilojoules_per_mole / nanometer,
            maxIterations=self.max_iterations,
        )

        if self.state_interval > 0:
            state = sim.context.getState(
                getPositions=True,
                getVelocities=True,
                getForces=True,
                getEnergy=True,
                enforcePeriodicBox=self.wrap_traj,
            )

            state_reporter = StateDataReporter(
                file=f"{dir_name / self.state_file_name}.csv",
                reportInterval=0,
                step=True,
                potentialEnergy=True,
                kineticEnergy=True,
                totalEnergy=True,
                temperature=True,
                volume=True,
                density=True,
            )
            state_reporter.report(sim, state)


@dataclass
class NPTMaker(BaseOpenMMMaker):

    name: str = "npt simulation"
    n_steps: int = 1_000_000
    pressure: float = 1
    pressure_update_frequency: int = 10

    def run_openmm(self, sim: Simulation, dir_name: Path) -> None:
        """Evolve the simulation for self.n_steps in the NPT ensemble.

        This adds a Monte Carlo barostat to the system to put it into NPT, runs the
        simulation for the specified number of steps, and then removes the barostat.

        Parameters
        ----------
        sim : Simulation
            The OpenMM simulation object.
        """
        context = sim.context
        system = context.getSystem()

        barostat_force_index = system.addForce(
            MonteCarloBarostat(
                self.pressure * atmosphere,
                sim.context.getIntegrator().getTemperature(),
                self.pressure_update_frequency,
            )
        )

        context.reinitialize(preserveState=True)

        sim.step(self.n_steps)

        system.removeForce(barostat_force_index)
        context.reinitialize(preserveState=True)


@dataclass
class NVTMaker(BaseOpenMMMaker):

    name: str = "nvt simulation"
    n_steps: int = 1_000_000

    def run_openmm(self, sim: Simulation, dir_name: Path) -> None:
        """Evolve the simulation with OpenMM for self.n_steps.

        Parameters
        ----------
        sim : Simulation
            The OpenMM simulation object.
        """
        sim.step(self.n_steps)


@dataclass
class TempChangeMaker(BaseOpenMMMaker):

    name: str = "temperature change"
    n_steps: int = 1_000_000
    temp_steps: int | None = None
    starting_temperature: float | None = None

    def run_openmm(self, sim: Simulation, dir_name: Path) -> None:
        """Evolve the simulation while gradually changing the temperature.

        self.temperature is the final temperature. self.temp_steps
        determines how many gradiations there are between the starting and
        final temperature. At each gradiation, the system is evolved for a
        number of steps such that the total number of steps is self.n_steps.

        Parameters
        ----------
        sim : Simulation
            The OpenMM simulation object.
        """
        integrator = sim.context.getIntegrator()

        temps = np.linspace(
            self.starting_temperature, self.temperature, self.temp_steps
        )
        steps = create_list_summing_to(self.n_steps, self.temp_steps)
        for temp, n_steps in zip(temps, steps, strict=True):
            integrator.setTemperature(temp * kelvin)
            sim.step(n_steps)

    def _create_integrator(
        self, prev_task: OpenMMTaskDocument | None = None
    ) -> Integrator:
        temp_steps_default = (self.n_steps // 10000) or 1
        self.temp_steps = self._resolve_attr(
            "temp_steps", prev_task, add_defaults={"temp_steps": temp_steps_default}
        )

        temp_holder, self.temperature = self.temperature, None
        self.starting_temperature = self._resolve_attr("temperature", prev_task)
        self.temperature = temp_holder or self._resolve_attr("temperature", prev_task)
        return LangevinMiddleIntegrator(
            self.starting_temperature * kelvin,
            self._resolve_attr("friction_coefficient", prev_task) / picoseconds,
            self._resolve_attr("step_size", prev_task) * picoseconds,
        )
