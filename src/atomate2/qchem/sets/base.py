
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from monty.io import zopen
from pymatgen.io.core import InputGenerator, InputSet
from pymatgen.io.qchem.inputs import QCInput
from pymatgen.io.qchem.utils import lower_and_check_unique

if TYPE_CHECKING:
    from pymatgen.core.structure import Molecule

__author__ = "Alex Ganose, Ryan Kingsbury, Rishabh D Guha"
__copyright__ = "Copyright 2018-2022, The Materials Project"
__version__ = "0.1"



class QCInputSet(InputSet):

    def __init__(
        self,
        qcinput: QCInput,
        optional_files: dict | None = None,
    ) -> None:
        self.qcinput = qcinput
        self.optional_files = {} if optional_files is None else optional_files

    def write_input(
        self,
        directory: str | Path,
        overwrite: bool = True,
    ) -> None:
        """Write QChem input file to directory.

        Parameters
        ----------
        directory
            Directory to write input files to.
        overwrite
            Whether to overwrite an input file if it already exists.
        """
        os.makedirs(directory, exist_ok=True)
        directory = Path(directory)

        inputs = {"Input_Dict": self.qcinput}
        inputs.update(self.optional_files)

        for key, val in inputs.items():
            inp_key = "mol.qin" if key == "Input_Dict" else f"{key}.qin"
            if val is not None and (overwrite or not (directory / inp_key).exists()):
                with zopen(directory / inp_key, "wt") as file:
                    file.write(str(val))
            elif not overwrite and (directory / inp_key).exists():
                raise FileExistsError(f"{directory / inp_key} already exists.")

    @staticmethod
    def from_directory(
        directory: str | Path, optional_files: dict = None
    ) -> QCInputSet:
        """Load a set of QChem inputs from a directory.

        Parameters
        ----------
        directory
            Directory to read QChem inputs from.
        optional_files
            Optional files to read in as well as a dict of {filename: Object class}.
            Object class must have a static/class method from_file
        """
        directory = Path(directory)
        objs = {"Input_Dict": QCInput}

        inputs = {}
        for name, obj in objs.items():
            file_path = directory / ("mol.qin" if name == "Input_Dict" else name)
            if file_path.exists():
                inputs[name.lower()] = obj.from_file(file_path)
        optional_inputs = {}
        if optional_files is not None:
            for name, obj in optional_files.items():
                optional_inputs[name] = obj.from_file(directory / name)

        return QCInputSet(inputs["input_dict"], optional_files=optional_inputs)



@dataclass
class QCInputGenerator(InputGenerator):

    job_type: str = field(default=None)
    basis_set: str = field(default=None)
    scf_algorithm: str = field(default=None)
    dft_rung: int = field(default=4)
    pcm_dielectric: float = field(default=None)
    smd_solvent: str = field(default=None)
    custom_smd: str = field(default=None)
    opt_dict: dict[str, Any] = field(default_factory=dict)
    scan_dict: dict[str, Any] = field(default_factory=dict)
    max_scf_cycles: int = field(default=100)
    geom_opt_max_cycles: int = field(default=200)
    plot_cubes: bool = field(default=False)
    nbo_params: dict[str, Any] = field(default_factory=dict)
    new_geom_opt: dict[str, Any] = field(default_factory=dict)
    overwrite_inputs: dict[str, str] = field(default_factory=dict)
    vdw_mode: Literal["atomic", "sequential"] = field(default="atomic")
    rem_dict: dict[str, Any] = field(default_factory=dict)
    vdw_dict: dict[str, float] = field(default_factory=dict)
    pcm_dict: dict[str, Any] = field(default_factory=dict)
    solv_dict: dict[str, Any] = field(default_factory=dict)
    smx_dict: dict[str, Any] = field(default_factory=dict)
    plots_dict: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Post init formatting of arguments."""
        self.rem_dict = {
            "job_type": self.job_type,
            "basis": self.basis_set,
            "max_scf_cycles": str(self.max_scf_cycles),
            "gen_scfman": "true",
            "xc_grid": "3",
            "thresh": "14",
            "s2thresh": "16",
            "scf_algorithm": self.scf_algorithm,
            "resp_charges": "true",
            "symmetry": "false",
            "sym_ignore": "true",
        }

        rung_2_func = ["spw92", "b97d3", "b97mv", "wb97mv", "wb97m(2)"]
        qc_method = {i + 1: e for i, e in enumerate(rung_2_func)}

        if qc_method.get(self.dft_rung):
            self.rem_dict["method"] = qc_method.get(self.dft_rung)
        else:
            raise ValueError("Provided DFT rung should be between 1 and 5!")

        if self.dft_rung == 2:
            self.rem_dict["dft_D"] = "D3_BJ"

        if self.job_type.lower() in ["opt", "ts", "pes_scan"]:
            self.rem_dict["geom_opt_max_cycles"] = str(self.geom_opt_max_cycles)

        if self.pcm_dielectric and self.smd_solvent:
            raise ValueError(
                "Only one of pcm or smd may be used as an implicit solvent. Not both!"
            )

        if self.pcm_dielectric:
            pcm_defaults = {
                "heavypoints": "194",
                "hpoints": "194",
                "radii": "uff",
                "theory": "cpcm",
                "vdwscale": "1.1",
            }

            self.pcm_dict = pcm_defaults
            self.solv_dict["dielectric"] = self.pcm_dielectric
            self.rem_dict["solvent_method"] = "pcm"

        if self.smd_solvent:
            if self.smd_solvent == "custom":
                self.smx_dict["solvent"] = "other"
            else:
                self.smx_dict["solvent"] = self.smd_solvent
            self.rem_dict["solvent_method"] = "smd"
            self.rem_dict["ideriv"] = "1"
            if self.smd_solvent in ("custom", "other") and self.custom_smd is None:
                raise ValueError(
                    "A user-defined SMD requires passing custom_smd,"
                    "a string of seven comma separated values in the following order: "
                    "dielectric, refractive index, acidity, basicity, surface tension,"
                    "aromaticity, electronegative halogenicity"
                )

        if self.plot_cubes:
            plots_defaults = {"grid_spacing": "0.05", "total_density": "0"}
            self.plots_dict = plots_defaults
            self.rem_dict["plots"] = "true"
            self.rem_dict["make_cube_files"] = "true"

        if self.nbo_params:
            self.rem_dict["nbo"] = "true"
            nbo_params_copy = self.nbo_params.copy()
            if "version" in nbo_params_copy:
                if nbo_params_copy["version"] == 7:
                    self.rem_dict["nbo_external"] = "true"
                else:
                    raise RuntimeError(
                        "nbo params version should only be set to 7! Exiting..."
                    )
            for key in nbo_params_copy:
                if key == "version":
                    self.nbo_params.pop(key)

        if self.new_geom_opt:
            self.rem_dict["geom_opt2"] = "3"

        if "maxiter" in self.new_geom_opt and self.new_geom_opt["maxiter"] != str(
            self.geom_opt_max_cycles
        ):
            raise RuntimeError(
                "Max # of optimization cycles must be the same! Exiting..."
            )

    def get_input_set(self, molecule: Molecule = None) -> QCInputSet:
        """Get a QChem InputSet for a molecule.

        Parameters
        ----------
        molecule: Molecule
            Pymatgen representation of a molecule for which the QCInputSet
            will be generated

        Returns
        -------
        QchemInputSet
            A QChem input set
        """
        if self.overwrite_inputs:
            for sub, sub_dict in self.overwrite_inputs.items():
                if sub == "rem":
                    temp_rem = lower_and_check_unique(sub_dict)
                    for k, v in temp_rem.items():
                        self.rem_dict[k] = v
                if sub == "pcm":
                    temp_pcm = lower_and_check_unique(sub_dict)
                    for k, v in temp_pcm.items():
                        self.pcm_dict[k] = v
                if sub == "solvent":
                    temp_solvent = lower_and_check_unique(sub_dict)
                    for k, v in temp_solvent.items():
                        self.solv_dict[k] = v
                if sub == "smx":
                    temp_smx = lower_and_check_unique(sub_dict)
                    for k, v in temp_smx.items():
                        self.smx_dict[k] = v
                if sub == "scan":
                    temp_scan = lower_and_check_unique(sub_dict)
                    for k, v in temp_scan.items():
                        self.scan_dict[k] = v
                if sub == "van_der_waals":
                    temp_vdw = lower_and_check_unique(sub_dict)
                    for k, v in temp_vdw.items():
                        self.vdw_dict[k] = v
                    self.pcm_dict["radii"] = "read"
                if sub == "plots":
                    temp_plots = lower_and_check_unique(sub_dict)
                    for k, v in temp_plots.items():
                        self.plots_dict[k] = v
                if sub == "nbo":
                    if self.nbo_dict is None:
                        raise RuntimeError(
                            "Can't overwrite nbo params when NBO"
                            "is not being run! Exiting..."
                        )
                    temp_nbo = lower_and_check_unique(sub_dict)
                    for k, v in temp_nbo.items():
                        self.nbo_dict[k] = v
                if sub == "geom_opt":
                    if self.geom_opt_dict is None:
                        raise RuntimeError(
                            "Can't overwrite geom_opt params when"
                            "not using the new optimizer! Exiting..."
                        )
                    temp_geomopt = lower_and_check_unique(sub_dict)
                    for k, v in temp_geomopt.items():
                        self.geom_opt_dict[k] = v
                if sub == "opt":
                    temp_opts = lower_and_check_unique(sub_dict)
                    for k, v in temp_opts.items():
                        self.opt_dict[k] = v

        return QCInputSet(
            qcinput=QCInput(
                molecule,
                rem=self.rem_dict,
                opt=self.opt_dict,
                pcm=self.pcm_dict,
                solvent=self.solv_dict,
                smx=self.smx_dict,
                scan=self.scan_dict,
                van_der_waals=self.vdw_dict,
                vdw_mode=self.vdw_mode,
                plots=self.plots_dict,
                nbo=self.nbo_params,
                geom_opt=self.new_geom_opt,
            )
        )
