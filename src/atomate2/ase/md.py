
from __future__ import annotations

import contextlib
import io
import logging
import os
import sys
import time
from abc import ABC
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from importlib import import_module
from typing import TYPE_CHECKING

import numpy as np
from ase import units
from ase.md.md import MolecularDynamics
from ase.md.npt import NPT
from ase.md.velocitydistribution import (
    MaxwellBoltzmannDistribution,
    Stationary,
    ZeroRotation,
)
from emmet.core.types.enums import StoreTrajectoryOption
from jobflow import job
from pymatgen.core.structure import Molecule, Structure
from pymatgen.io.ase import AseAtomsAdaptor
from scipy.interpolate import interp1d

from atomate2 import SETTINGS
from atomate2.ase.jobs import _ASE_DATA_OBJECTS, AseMaker
from atomate2.ase.schemas import AseResult, AseTaskDoc
from atomate2.ase.utils import TrajectoryObserver

if TYPE_CHECKING:
    from pathlib import Path
    from typing import Literal

    from ase.calculators.calculator import Calculator

    from atomate2.ase.schemas import AseMoleculeTaskDoc, AseStructureTaskDoc

logger = logging.getLogger(__name__)


class MDEnsemble(Enum):

    nve = "nve"
    nvt = "nvt"
    npt = "npt"


class DynamicsPresets(Enum):

    nve_velocityverlet = "ase.md.verlet.VelocityVerlet"
    nvt_andersen = "ase.md.andersen.Andersen"
    nvt_berendsen = "ase.md.nvtberendsen.NVTBerendsen"
    nvt_langevin = "ase.md.langevin.Langevin"
    nvt_nose_hoover = "ase.md.npt.NPT"
    npt_berendsen = "ase.md.nptberendsen.NPTBerendsen"
    npt_nose_hoover = "ase.md.npt.NPT"  # noqa: PIE796
    npt_nose_hoover_chain = "ase.md.nose_hoover_chain.MTKNPT"


default_dynamics = {
    MDEnsemble.nve: "velocityverlet",
    MDEnsemble.nvt: "langevin",
    MDEnsemble.npt: "nose-hoover-chain",
}

_valid_dynamics: dict[MDEnsemble, set[str]] = {}
for preset in DynamicsPresets.__members__:
    ensemble = MDEnsemble(preset.split("_")[0])
    thermostat = "-".join(preset.split("_")[1:])
    if ensemble not in _valid_dynamics:
        _valid_dynamics[ensemble] = set()
    _valid_dynamics[ensemble].add(thermostat)


@dataclass
class AseMDMaker(AseMaker, ABC):

    name: str = "ASE MD"
    time_step: float | None = None
    n_steps: int = 1000
    ensemble: MDEnsemble = MDEnsemble.nvt
    dynamics: str | MolecularDynamics | None = None
    temperature: float | Sequence | np.ndarray | None = 300.0
    pressure: float | Sequence | np.ndarray | None = None
    ase_md_kwargs: dict | None = None
    calculator_kwargs: dict = field(default_factory=dict)
    ionic_step_data: tuple[str, ...] | None = None
    store_trajectory: StoreTrajectoryOption = StoreTrajectoryOption.PARTIAL
    traj_file: str | Path | None = None
    traj_file_fmt: Literal["pmg", "ase", "xdatcar"] = "ase"
    traj_interval: int = 1
    mb_velocity_seed: int | None = None
    zero_linear_momentum: bool = False
    zero_angular_momentum: bool = False
    verbose: bool = False
    use_emmet_models: bool = SETTINGS.ASE_FORCEFIELD_USE_EMMET_MODELS

    def __post_init__(self) -> None:
        """Ensure that ensemble is an enum."""
        super().__post_init__()
        if isinstance(self.ensemble, str):
            self.ensemble = MDEnsemble(self.ensemble.split("MDEnsemble.")[-1])

    @staticmethod
    def _interpolate_quantity(values: Sequence | np.ndarray, n_pts: int) -> np.ndarray:
        """Interpolate temperature / pressure on a schedule."""
        n_vals = len(values)
        return np.interp(
            np.linspace(0, n_vals - 1, n_pts + 1),
            np.linspace(0, n_vals - 1, n_vals),
            values,
        )

    def _get_ensemble_schedule(self) -> None:
        if self.ensemble == MDEnsemble.nve:
            self.temperature = np.nan
            self.pressure = np.nan
            self.t_schedule = np.full(self.n_steps + 1, self.temperature)
            self.p_schedule = np.full(self.n_steps + 1, self.pressure)
            return

        if isinstance(self.temperature, Sequence) or (
            isinstance(self.temperature, np.ndarray) and self.temperature.ndim == 1
        ):
            self.t_schedule = self._interpolate_quantity(self.temperature, self.n_steps)
        else:
            self.t_schedule = np.full(self.n_steps + 1, self.temperature)

        if self.ensemble == MDEnsemble.nvt:
            self.pressure = np.nan
            self.p_schedule = np.full(self.n_steps + 1, self.pressure)
            return

        if isinstance(self.pressure, Sequence) or (
            isinstance(self.pressure, np.ndarray) and self.pressure.ndim == 1
        ):
            self.p_schedule = self._interpolate_quantity(self.pressure, self.n_steps)
        elif isinstance(self.pressure, np.ndarray) and self.pressure.ndim == 4:
            self.p_schedule = interp1d(
                np.arange(self.n_steps + 1), self.pressure, kind="linear"
            )
        else:
            self.p_schedule = np.full(self.n_steps + 1, self.pressure)

    def _get_ensemble_defaults(self) -> None:
        """Update ASE MD kwargs with defaults consistent with VASP MD."""
        self.ase_md_kwargs = self.ase_md_kwargs or {}
        self.dynamics = self.dynamics or default_dynamics[self.ensemble]

        if self.ensemble == MDEnsemble.nve:
            self.ase_md_kwargs.pop("temperature", None)
            self.ase_md_kwargs.pop("temperature_K", None)
            self.ase_md_kwargs.pop("externalstress", None)
        elif self.ensemble == MDEnsemble.nvt:
            self.ase_md_kwargs["temperature_K"] = self.ase_md_kwargs.get(
                "temperature_K", self.t_schedule[0]
            )
            self.ase_md_kwargs.pop("externalstress", None)
        elif self.ensemble == MDEnsemble.npt:
            self.ase_md_kwargs["temperature_K"] = self.ase_md_kwargs.get(
                "temperature_K", self.t_schedule[0]
            )

            if (
                (
                    isinstance(self.dynamics, DynamicsPresets)
                    and DynamicsPresets(self.dynamics)
                    == DynamicsPresets.npt_nose_hoover
                )
                or (
                    isinstance(self.dynamics, type)
                    and issubclass(self.dynamics, MolecularDynamics)
                    and self.dynamics.__name__ == "NPT"
                )
                or (isinstance(self.dynamics, str) and self.dynamics == "nose-hoover")
            ):
                logger.warning(
                    "The `NPT` module in ASE is no longer recommended."
                    "Users are advised to switch to Nose-Hoover chain / MTKNPT."
                )
                stress_kwarg = "externalstress"
            else:
                stress_kwarg = "pressure_au"

            self.ase_md_kwargs[stress_kwarg] = self.ase_md_kwargs.get(
                stress_kwarg, self.p_schedule[0] * 1e3 * units.bar
            )

        if isinstance(self.dynamics, str) and self.dynamics.lower() == "langevin":
            self.ase_md_kwargs["friction"] = self.ase_md_kwargs.get(
                "friction",
                10.0 * 1e-3 / units.fs,  # Same default as in VASP: 10 ps^-1
            )

    @job(data=[*_ASE_DATA_OBJECTS, "ionic_steps"])
    def make(
        self,
        mol_or_struct: Molecule | Structure,
        prev_dir: str | Path | None = None,
    ) -> AseStructureTaskDoc | AseMoleculeTaskDoc:
        """
        Perform MD on a structure using ASE and jobflow.

        Parameters
        ----------
        mol_or_struct: .Molecule or .Structure
            pymatgen molecule or structure
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
            added to match the method signature of other makers.
        """
        return AseTaskDoc.to_mol_or_struct_metadata_doc(
            getattr(self.calculator, "name", type(self.calculator).__name__),
            self.run_ase(mol_or_struct, prev_dir=prev_dir),
            steps=self.n_steps,
            relax_kwargs=None,
            optimizer_kwargs=None,
            fix_symmetry=False,
            symprec=None,
            ionic_step_data=self.ionic_step_data,
            store_trajectory=self.store_trajectory,
            tags=self.tags,
        )

    def run_ase(
        self,
        mol_or_struct: Molecule | Structure,
        prev_dir: str | Path | None = None,
    ) -> AseResult:
        """
        Perform MD on a structure using ASE without jobflow.

        This function is implemented to permit different schemas on output.
        See for example, the forcefield MD jobs.

        Parameters
        ----------
        mol_or_struct: .Molecule or .Structure
            pymatgen molecule or structure
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from. Unused, just
            added to match the method signature of other makers.
        """
        self._get_ensemble_schedule()
        self._get_ensemble_defaults()

        if self.time_step is None:
            has_h_isotope = any(element.Z == 1 for element in mol_or_struct.composition)
            self.time_step = 0.5 if has_h_isotope else 2.0

        initial_velocities = mol_or_struct.site_properties.get("velocities")

        if isinstance(self.dynamics, str):
            self.dynamics = self.dynamics.lower()
            if self.dynamics not in _valid_dynamics[self.ensemble]:
                raise ValueError(
                    f"{self.dynamics} thermostat not available for "
                    f"{self.ensemble.value}. "
                    f"Available {self.ensemble.value} thermostats are: "
                    " ".join(_valid_dynamics[self.ensemble])
                )

            _dyn_mod_path = DynamicsPresets[
                f"{self.ensemble.value}_{self.dynamics.replace('-', '_')}"
            ].value.split(".")
            dynamics = getattr(
                import_module(".".join(_dyn_mod_path[:-1])), _dyn_mod_path[-1]
            )

        elif issubclass(self.dynamics, MolecularDynamics):
            dynamics = self.dynamics

        atoms = mol_or_struct.to_ase_atoms()

        if dynamics is NPT:

            atoms.set_cell(atoms.cell.standard_form(form="upper")[0])

        if initial_velocities:
            atoms.set_velocities(initial_velocities)
        elif not np.isnan(self.t_schedule).any():
            MaxwellBoltzmannDistribution(
                atoms=atoms,
                temperature_K=self.t_schedule[0],
                rng=np.random.default_rng(seed=self.mb_velocity_seed),
            )
            if self.zero_linear_momentum:
                Stationary(atoms)
            if self.zero_angular_momentum:
                ZeroRotation(atoms)

        atoms.calc = self.calculator

        md_observer = TrajectoryObserver(atoms, store_md_outputs=True)

        md_runner = dynamics(
            atoms=atoms, timestep=self.time_step * units.fs, **self.ase_md_kwargs
        )

        md_runner.attach(md_observer, interval=self.traj_interval)


        md_runner.attach(_callback, interval=1)
        with contextlib.redirect_stdout(sys.stdout if self.verbose else io.StringIO()):
            t_i = time.perf_counter()
            md_runner.run(steps=self.n_steps)
            t_f = time.perf_counter()

        if self.traj_file is not None:
            md_observer.save(filename=self.traj_file, fmt=self.traj_file_fmt)

        mol_or_struct = AseAtomsAdaptor.get_structure(
            atoms,
            cls=Structure if isinstance(mol_or_struct, Structure) else Molecule,
        )

        return AseResult(
            final_mol_or_struct=mol_or_struct,
            trajectory=getattr(
                md_observer,
                "to_emmet_trajectory"
                if self.use_emmet_models
                else "to_pymatgen_trajectory",
            )(filename=None),
            dir_name=os.getcwd(),
            elapsed_time=t_f - t_i,
        )


@dataclass
class LennardJonesMDMaker(AseMDMaker):

    name: str = "Lennard-Jones 6-12 MD"

    def _get_calculator(self) -> Calculator:
        pass


@dataclass
class GFNxTBMDMaker(AseMDMaker):

    name: str = "GFNn-xTB MD"
    calculator_kwargs: dict = field(
        default_factory=lambda: {
            "method": "GFN1-xTB",
            "charge": None,
            "multiplicity": None,
            "accuracy": 1.0,
            "guess": "sad",
            "max_iterations": 250,
            "mixer_damping": 0.4,
            "electric_field": None,
            "spin_polarization": None,
            "electronic_temperature": 300.0,
            "cache_api": True,
            "verbosity": 1,
        }
    )

    def _get_calculator(self) -> Calculator:
        pass
