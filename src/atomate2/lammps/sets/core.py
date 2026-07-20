
from dataclasses import dataclass, field

from pymatgen.io.lammps.generators import (
    _BASE_LAMMPS_SETTINGS,
    BaseLammpsSetGenerator,
    LammpsSettings,
)

from atomate2.ase.md import MDEnsemble


@dataclass
class LammpsNVESet(BaseLammpsSetGenerator):

    ensemble: MDEnsemble = field(default=MDEnsemble.nve)
    settings: LammpsSettings | dict | None = field(default=None)

    def __post_init__(self) -> None:
        """Initialize NVE-specific settings and defaults."""
        self.calc_type = f"lammps_{self.ensemble.value}"
        if self.settings is None:
            settings_dict = {}
        elif isinstance(self.settings, LammpsSettings):
            settings_dict = self.settings.as_dict()
        else:
            settings_dict = self.settings.copy()
        settings_dict.update(
            {
                "ensemble": self.ensemble.value,
                "thermostat": None,
                "barostat": None,
                "friction": None,
            }
        )
        self.settings = settings_dict
        super().__post_init__()


@dataclass
class LammpsNVTSet(BaseLammpsSetGenerator):

    ensemble: MDEnsemble = field(default=MDEnsemble.nvt)
    settings: LammpsSettings | dict | None = field(default=None)

    def __post_init__(self) -> None:
        """Initialize NVT-specific settings and defaults."""
        self.calc_type = f"lammps_{self.ensemble.value}"
        if self.settings is None:
            settings_dict = {}
        elif isinstance(self.settings, LammpsSettings):
            settings_dict = self.settings.as_dict()
        else:
            settings_dict = self.settings.copy()

        settings_dict.update(
            {
                "ensemble": self.ensemble.value,
                "thermostat": settings_dict.get("thermostat", "langevin"),
                "start_temp": settings_dict.get("start_temp", 300.0),
                "end_temp": settings_dict.get("end_temp", 300.0),
                "friction": settings_dict.get(
                    "friction", _BASE_LAMMPS_SETTINGS["periodic"]["friction"]
                ),
            }
        )

        self.settings = settings_dict
        super().__post_init__()


@dataclass
class LammpsNPTSet(BaseLammpsSetGenerator):

    ensemble: MDEnsemble = field(default=MDEnsemble.npt)
    settings: LammpsSettings | dict | None = field(default=None)

    def __post_init__(self) -> None:
        """Initialize NPT-specific settings and defaults."""
        self.calc_type = f"lammps_{self.ensemble.value}"
        if self.settings is None:
            settings_dict = {}
        elif isinstance(self.settings, LammpsSettings):
            settings_dict = self.settings.as_dict()
        else:
            settings_dict = self.settings.copy()

        settings_dict.update(
            {
                "ensemble": self.ensemble.value,
                "barostat": settings_dict.get("barostat", "nose-hoover"),
                "start_pressure": settings_dict.get("start_pressure", 1.0),
                "end_pressure": settings_dict.get("end_pressure", 1.0),
                "start_temp": settings_dict.get("start_temp", 300),
                "end_temp": settings_dict.get("end_temp", 300),
                "friction": settings_dict.get(
                    "friction", _BASE_LAMMPS_SETTINGS["periodic"]["friction"]
                ),
                "psymm": settings_dict.get("psymm", "iso"),
            }
        )

        self.settings = settings_dict
        super().__post_init__()


@dataclass
class LammpsMinimizeSet(BaseLammpsSetGenerator):

    settings: LammpsSettings | dict | None = field(default=None)

    def __post_init__(self) -> None:
        """Initialize minimization-specific settings and defaults."""
        self.calc_type = "lammps_minimization"
        if self.settings is None:
            settings_dict = {}
        elif isinstance(self.settings, LammpsSettings):
            settings_dict = self.settings.as_dict()
        else:
            settings_dict = self.settings.copy()

        settings_dict.update(
            {
                "ensemble": "minimize",
                "nsteps": settings_dict.get("nsteps", 10000),
                "start_pressure": settings_dict.get("start_pressure", 0),
                "end_pressure": settings_dict.get("end_pressure", 0),
                "tol": settings_dict.get("tol", 1.0e-6),
                "thermo": settings_dict.get(
                    "thermo", 5
                ),  # Use 5 for minimization like reference
                "traj_interval": settings_dict.get(
                    "traj_interval", 5
                ),  # Use 5 for minimization like reference
            }
        )

        self.settings = settings_dict
        super().__post_init__()
