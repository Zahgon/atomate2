
from __future__ import annotations

import io
import os
import re
import shutil
import tempfile
import time
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import openmm.unit as omm_unit
from openmm import (
    CustomNonbondedForce,
    LangevinMiddleIntegrator,
    NonbondedForce,
    State,
    System,
    XmlSerializer,
)
from openmm.app import PDBFile, Simulation
from pymatgen.core.trajectory import Trajectory

from atomate2.openmm.interchange import OpenMMInterchange

if TYPE_CHECKING:
    from emmet.core.openmm import OpenMMTaskDocument
    from openff.interchange import Interchange


def download_opls_xml(
    names_params: dict[str, dict[str, str]],
    output_dir: str | Path,
    overwrite_files: bool = False,
) -> None:
    """Download an OPLS-AA/M XML file from the LigParGen website using Selenium."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as ec
        from selenium.webdriver.support.ui import WebDriverWait
        from webdriver_manager.chrome import ChromeDriverManager

    except ImportError:
        warnings.warn(
            "The `selenium` or `webdriver_manager` package is not installed. "
            "It's required to run the opls web scraper.",
            stacklevel=1,
        )

    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

    for name, params in names_params.items():
        final_file = Path(output_dir) / f"{name}.xml"
        smiles = params.get("smiles")
        charge = params.get("charge", 0)
        checkopt = params.get("checkopt", 3)

        if final_file.exists() and not overwrite_files:
            continue
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                download_dir = tmpdir

                chrome_options = webdriver.ChromeOptions()
                prefs = {"download.default_directory": download_dir}
                chrome_options.add_experimental_option("prefs", prefs)

                driver = webdriver.Chrome(options=chrome_options)

                driver.get("https://zarbi.chem.yale.edu/ligpargen/")

                smiles_input = WebDriverWait(driver, 10).until(
                    ec.presence_of_element_located((By.ID, "smiles"))
                )
                smiles_input.send_keys(smiles)

                checkopt_input = WebDriverWait(driver, 10).until(
                    ec.presence_of_element_located((By.NAME, "checkopt"))
                )
                checkopt_input.send_keys(checkopt)

                charge_input = WebDriverWait(driver, 10).until(
                    ec.presence_of_element_located((By.NAME, "dropcharge"))
                )
                charge_input.send_keys(charge)

                submit_button = driver.find_element(
                    By.XPATH,
                    '//button[@type="submit" and contains(text(), "Submit Molecule")]',
                )
                submit_button.click()

                time.sleep(
                    2 + 0.5 * int(checkopt)
                )  # Adjust based on loading time and optimization iterations

                xml_button = driver.find_element(
                    By.XPATH, '//input[@type="submit" and @value="XML"]'
                )
                xml_button.click()

                time.sleep(0.3)  # Adjust as needed based on the download time

                file = next(Path(tmpdir).iterdir())

                shutil.move(file, final_file)

        except Exception as e:  # noqa: BLE001
            warnings.warn(
                f"{name} ({smiles}) failed to download because an error occurred: {e}",
                stacklevel=1,
            )

    driver.quit()


def generate_opls_xml(
    names_params: dict[str, dict[str, str]],
    output_dir: str | Path,
    overwrite_files: bool = False,
) -> None:
    """Download an OPLS-AA/M XML file from the LigParGen repo & BOSS executable.

    Parameters
    ----------
    names_params : dict[str, dict[str, str]]
        Dictionary where keys are molecule names and values are dictionaries,
        with keys:
        - smiles : str
            SMILES representation of molecule (required).
        Optional Parameters:
            - charge : str, optional
                Net charge of molecule (default is "0"). If non-zero, must include "-"
                or "+" sign before integer.
            - checkopt : str, optional
                Molecule optimization iterations from 0-3 (default is "3").
            - cgen : str, optional
                Charge model, either "CM1A-LBCC" (neutral molecules) or (default) "CM1A"
                (neutral or charged molecules).

    """
    import subprocess

    if os.getenv("CONTAINER_SOFTWARE") is None:
        raise OSError("CONTAINER_SOFTWARE env variable not set.")
    if os.getenv("LPG_IMAGE_NAME") is None:
        raise OSError("LPG_IMAGE_NAME env variable not set.")
    for name, params in names_params.items():
        output_dir = Path(output_dir)
        final_file = output_dir / f"{name}.xml"
        smiles = params.get("smiles")
        charge = params.get("charge", 0)
        charge_method = params.get("cgen", "CM1A")
        checkopt = params.get("checkopt", 3)

        if final_file.exists() and not overwrite_files:
            continue
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                download_dir = tmpdir

                lpg_cmd = [
                    f"ligpargen -n {name} -p {name} "
                    f"-r {name} -c {charge} -o {checkopt} "
                    f"-cgen {charge_method} -s '{smiles}'"
                ]
                run_container = (
                    f"{os.environ['CONTAINER_SOFTWARE']} "
                    f"run --rm -v {download_dir}:/opt/output "
                    f"{os.environ['LPG_IMAGE_NAME']} bash -c"
                )
                subprocess.run(run_container.split() + lpg_cmd, check=False)

                file = Path(download_dir) / f"{name}" / f"{name}.openmm.xml"

                output_dir.mkdir(parents=True, exist_ok=True)
                shutil.move(file, final_file)

        except Exception as e:  # noqa: BLE001
            warnings.warn(
                f"{name} ({params}) failed to download because an error occurred: {e}",
                stacklevel=1,
            )


def create_list_summing_to(total_sum: int, n_pieces: int) -> list:
    """Create a NumPy array with n_pieces elements that sum up to total_sum.

    Divides total_sum by n_pieces to determine the base value for each element.
    Distributes the remainder evenly among the elements.

    Parameters
    ----------
    total_sum : int
        The desired sum of the array elements.
    n_pieces : int
        The number of elements in the array.

    Returns
    -------
    numpy.ndarray
        A 1D NumPy array with n_pieces elements summing up to total_sum.
    """
    div, mod = total_sum // n_pieces, total_sum % n_pieces
    return [div + 1] * mod + [div] * (n_pieces - mod)


def increment_name(file_name: str) -> str:
    """Increment the count in a file name."""
    re_match = re.search(r"(\d*)$", file_name)
    position = re_match.start(1)
    new_count = int(re_match.group(1) or 1) + 1
    return f"{file_name[:position]}{new_count}"


def task_reports(task: OpenMMTaskDocument, traj_or_state: str = "traj") -> bool:
    """Check if a task reports trajectories or states."""
    if not task.calcs_reversed:
        return False
    calc_input = task.calcs_reversed[0].input
    if traj_or_state == "traj":
        report_freq = calc_input.traj_interval
    elif traj_or_state == "state":
        report_freq = calc_input.state_interval
    else:
        raise ValueError("traj_or_state must be 'traj' or 'state'")
    return calc_input.n_steps >= report_freq


def openff_to_openmm_interchange(
    openff_interchange: Interchange,
) -> OpenMMInterchange:
    pass


def opls_lj(system: System) -> System:
    """Update system object combination rules to geometric mean for OPLS convention.

    Except for OPLS-AA, most force fields implement the Lorentz-Berthelot
    combination rules to obtain epsilon and sigma values. This is also the only
    combination rule implemented in OpenMM. Herein is a function call to use the
    OPLS-AA geometric combination rules.

    Ref: https://traken.chem.yale.edu/ligpargen/openMM_tutorial.html
    See Section 4.1.1 of Gromac Manual for further details.

    Note: OPLS-AA uses the 0.5 scaling factor for 1-4 interactions. LigParGen creates
    xml files that are consistent with this selection, but if not, the NonbondedForce
    class should be as follows:

    <NonbondedForce coulomb14scale="0.5" lj14scale="0.5">
    """
    forces = {
        system.getForce(index).__class__.__name__: system.getForce(index)
        for index in range(system.getNumForces())
    }
    nonbonded_force = forces["NonbondedForce"]
    lorentz = CustomNonbondedForce(
        """4*epsilon*((sigma/r)^12-(sigma/r)^6);
        sigma=sqrt(sigma1*sigma2);
        epsilon=sqrt(epsilon1*epsilon2)"""
    )
    lorentz.setNonbondedMethod(
        min(nonbonded_force.getNonbondedMethod(), NonbondedForce.CutoffPeriodic)
    )
    lorentz.addPerParticleParameter("sigma")
    lorentz.addPerParticleParameter("epsilon")
    lorentz.setCutoffDistance(nonbonded_force.getCutoffDistance())
    system.addForce(lorentz)
    ljset = {}
    for index in range(nonbonded_force.getNumParticles()):
        charge, sigma, epsilon = nonbonded_force.getParticleParameters(index)
        ljset[index] = (sigma, epsilon)
        lorentz.addParticle([sigma, epsilon])
        nonbonded_force.setParticleParameters(index, charge, sigma, epsilon * 0)
    for i in range(nonbonded_force.getNumExceptions()):
        (p1, p2, q, _, eps) = nonbonded_force.getExceptionParameters(i)
        lorentz.addExclusion(p1, p2)
        if eps.value_in_unit(eps.unit) != 0.0:
            sig14 = omm_unit.sqrt(ljset[p1][0] * ljset[p2][0])
            nonbonded_force.setExceptionParameters(i, p1, p2, q, sig14, eps)
    return system


class PymatgenTrajectoryReporter:

    def __init__(
        self,
        file: str | Path,
        reportInterval: int,  # noqa: N803
        enforcePeriodicBox: bool | None = None,  # noqa: N803
    ) -> None:
        """Initialize the reporter.

        Parameters
        ----------
        file : str | Path
            The file to write the trajectory to
        reportInterval : int
            The interval (in time steps) at which to save frames
        enforcePeriodicBox : bool | None
            Whether to wrap coordinates to the periodic box. If None, determined from
            simulation settings.
        """
        self._file = file
        self._reportInterval = reportInterval
        self._enforcePeriodicBox = enforcePeriodicBox
        self._topology = None
        self._nextModel = 0

        self._positions: list[np.ndarray] = []
        self._velocities: list[np.ndarray] = []
        self._lattices: list[np.ndarray] = []
        self._frame_properties: list[dict] = []
        self._species: list[str] | None = None
        self._time_step: float | None = None

    def describeNextReport(  # noqa: N802
        self, simulation: Simulation
    ) -> tuple[int, bool, bool, bool, bool, bool]:
        pass

    def report(self, simulation: Simulation, state: State) -> None:
        """Generate a report.

        Parameters
        ----------
        simulation : Simulation
            The Simulation to generate a report for
        state : State
            The current state of the simulation
        """
        if self._nextModel == 0:
            self._topology = simulation.topology
            self._species = [
                atom.element.symbol for atom in simulation.topology.atoms()
            ]
            self._time_step = (
                simulation.integrator.getStepSize() * self._reportInterval
            ).value_in_unit(omm_unit.femtoseconds)

        positions = state.getPositions(asNumpy=True).value_in_unit(omm_unit.angstrom)
        velocities = state.getVelocities(asNumpy=True).value_in_unit(
            omm_unit.angstrom / omm_unit.femtosecond
        )
        box_vectors = state.getPeriodicBoxVectors(asNumpy=True).value_in_unit(
            omm_unit.angstrom
        )

        kinetic_energy = (
            state.getKineticEnergy() / omm_unit.AVOGADRO_CONSTANT_NA
        ).value_in_unit(omm_unit.ev)

        potential_energy = (
            state.getPotentialEnergy() / omm_unit.AVOGADRO_CONSTANT_NA
        ).value_in_unit(omm_unit.ev)

        self._positions.append(positions)
        self._velocities.append(velocities)
        self._lattices.append(box_vectors)
        self._frame_properties.append(
            {
                "kinetic_energy": kinetic_energy,
                "potential_energy": potential_energy,
                "total_energy": kinetic_energy + potential_energy,
            }
        )

        self._nextModel += 1

    def save(self) -> None:
        """Write accumulated trajectory data to a pymatgen Trajectory object."""
        if not self._positions:
            return

        velocities = [
            [tuple(site_vel) for site_vel in frame_vel]
            for frame_vel in self._velocities
        ]

        site_properties = []
        n_frames = len(self._positions)
        site_properties = [{"velocities": velocities[i]} for i in range(n_frames)]

        trajectory = Trajectory(
            species=self._species,
            coords=self._positions,
            lattice=self._lattices,
            frame_properties=self._frame_properties,
            site_properties=site_properties,  # Now properly formatted as list of dicts
            time_step=self._time_step,
        )

        self.trajectory = trajectory

        with open(self._file, mode="w") as file:
            file.write(trajectory.to_json())
