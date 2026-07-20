
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np
from jobflow import job
from monty.json import MSONable
from pymatgen.alchemy.materials import TransformedStructure
from pymatgen.analysis.eos import EOS, EOSError
from pymatgen.transformations.standard_transformations import (
    DeformStructureTransformation,
)
from scipy.optimize import leastsq

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

    from jobflow import Job
    from pymatgen.core import Structure


class EOSPostProcessor(MSONable, ABC):

    name: str = "EOS postprocessor"
    eos_attrs: tuple[str, ...] = ("energy", "volume", "stress", "pressure")
    job_types: tuple[str, ...] = ("relax", "static")
    min_data_points: int | None = None

    def __init__(self) -> None:
        self.results: dict[str, dict] = {}

    def sort_by_quantity(self, quantity: str = "volume") -> None:
        """
        Sort input data by given kwarg.

        Parameters
        ----------
        quantity : str = "volume"
            kwarg to sort by
        """
        for job_type in self._use_job_types:
            sort_by_vol = np.argsort(self.results[job_type][quantity])
            for key in self.eos_attrs:
                if self.results[job_type].get(key):
                    self.results[job_type][key] = [
                        self.results[job_type][key][index] for index in sort_by_vol
                    ]

    @abstractmethod
    def eval(self) -> None:
        """Fit the EOS according to a user-implemented function."""
        raise NotImplementedError

    def fit(self, eos_flow_output: dict[str, Any]) -> None:
        """
        Fit the EOS.

        Parameters
        ----------
        eos_flow_output : dict
            Volume, energy, and (optionally) stress and pressure data in dict
            form::

                {
                    "relax" <required> and "static" <optional> : {
                        "energy": list, <required>
                        "volume": list, <required>
                        "stress": list <optional>
                        "structure": list <not needed for the fit>
                        "dir_name": list <optional for the fit>
                    },
                    "initial_<key>": {"E0": float, "V0": float} <optional>,
                        for <key> in ("relax", "static")
                }

        """
        self.results.update(eos_flow_output)
        self._use_job_types = [key for key in self.job_types if self.results.get(key)]
        if self.min_data_points and any(
            len(self.results[job_type].get("volume", [])) < self.min_data_points
            for job_type in self._use_job_types
        ):
            raise ValueError(
                f"{type(self)} requires {self.min_data_points} frames to fit an EOS."
            )

        self.sort_by_quantity()
        self.eval()

    @job
    def make(self, eos_flow_output: dict[str, Any]) -> Job:
        """Run the fit as a jobflow job.

        Parameters
        ----------
        eos_flow_output : dict
            Volume, energy, and (optionally) stress and pressure data in dict
            form::

                {
                    "relax" <required> and "static" <optional> : {
                        "energy": list, <required>
                        "volume": list, <required>
                        "stress": list <optional>
                    },
                    "initial_<key>": {"E0": float, "V0": float} <optional>,
                        for <key> in ("relax", "static")
                }

        """
        self.fit(eos_flow_output)
        return self.results


class PostProcessEosEnergy(EOSPostProcessor):

    name: str = "EOS energy vs volume fit"
    min_data_points: int | None = 4
    eos_models: tuple[str, ...] = (
        "murnaghan",
        "birch",
        "birch_murnaghan",
        "pourier_tarantola",
        "vinet",
    )

    def eval(self) -> None:
        """Fit the input data to each EOS in ``self.eos_models``."""
        for jobtype in self._use_job_types:
            self.results[jobtype]["EOS"] = {}
            for eos_name in self.eos_models:
                try:
                    eos = EOS(eos_name=eos_name).fit(
                        self.results[jobtype]["volume"], self.results[jobtype]["energy"]
                    )
                    self.results[jobtype]["EOS"][eos_name] = {
                        **eos.results,
                        "b0 GPa": float(eos.b0_GPa),
                    }
                except EOSError as exc:
                    self.results[jobtype]["EOS"][eos_name] = {"exception": str(exc)}


class PostProcessEosPressure(EOSPostProcessor):

    name: str = "EOS pressure vs volume fit"
    min_data_points: int | None = 3

    @staticmethod
    def _birch_murnaghan_pressure(
        volume: float, b0: float, b1: float, v0: float
    ) -> float:
        pass

    def _initial_fit(self) -> dict:
        """Generate initial polynomial fit for p(V) curve.

        ::
            p(V) / V = a + b V + c V**2
        """
        init_pars = {}
        for jobtype in self._use_job_types:
            if self.results[jobtype].get("stress") and (
                not self.results[jobtype].get("pressure")
            ):
                self.results[jobtype]["pressure"] = [
                    1.0 / 3.0 * np.trace(np.array(stress_tensor))
                    for stress_tensor in self.results[jobtype]["stress"]
                ]
            poly_pars = np.polyfit(
                self.results[jobtype]["volume"],
                np.array(self.results[jobtype]["pressure"])
                / np.array(self.results[jobtype]["volume"]),
                deg=2,
            )

            radicand = poly_pars[1] ** 2 - 4.0 * poly_pars[0] * poly_pars[2]
            if radicand < 0.0:
                v0 = self.results[jobtype]["volume"][
                    np.argmin(self.results[jobtype]["energy"])
                ]
            else:
                min_abs_pressure = 1e20
                for i in range(2):
                    _v0 = (-poly_pars[1] + (-1) ** i * radicand ** (0.5)) / (
                        2.0 * poly_pars[0]
                    )
                    pressure = _v0 * np.polyval(poly_pars, _v0)
                    if _v0 > 0.0 and abs(pressure) < min_abs_pressure:
                        min_abs_pressure = abs(pressure)
                        v0 = _v0

            b0 = -(
                3 * poly_pars[0] * v0**3 + 2 * poly_pars[1] * v0**2 + poly_pars[0] * v0
            )
            b1 = (
                v0
                * (9 * poly_pars[0] * v0**2 + 4 * poly_pars[1] * v0 + poly_pars[0])
                / b0
            )

            init_pars[jobtype] = [b0, b1, v0]

        return init_pars


    def eval(self) -> None:
        """Fit the input data to the Birch-Murnaghan pressure EOS."""
        initial_pars = self._initial_fit()
        for jobtype in self._use_job_types:
            eos_params, ierr = leastsq(
                self._objective, initial_pars[jobtype], args=(jobtype,)
            )

            self.results[jobtype]["EOS"] = {}
            if ierr not in (1, 2, 3, 4):
                self.results[jobtype]["EOS"]["exception"] = (
                    "Optimal EOS parameters not found."
                )
            else:
                for i, key in enumerate(["b0", "b1", "v0"]):
                    self.results[jobtype]["EOS"][key] = eos_params[i]


@job
def apply_strain_to_structure(structure: Structure, deformations: list) -> list:
    """
    Apply strain(s) to input structure and return transformation(s) as list.

    Parameters
    ----------
    structure: .Structure
        Input structure to apply strain to
    deformations: list[.Deformation]
        A list of deformations to apply **independently** to the input
        structure, in anticipation of performing an EOS fit.
        Deformations should be of the form of a 3x3 matrix, e.g.,::

        [[1.2, 0., 0.], [0., 1.2, 0.], [0., 0., 1.2]]

        or::

        ((1.2, 0., 0.), (0., 1.2, 0.), (0., 0., 1.2))

    Returns
    -------
    list
        A list of .TransformedStructure objects corresponding to the
        list of input deformations.
    """
    transformations = []
    for deformation in deformations:
        ts = TransformedStructure(
            structure,
            transformations=[DeformStructureTransformation(deformation=deformation)],
        )
        transformations += [ts]
    return transformations


def _apply_strain_to_structure(structure: Structure, deformations: list) -> list:
    """
    Apply strain(s) to input structure and return transformation(s) as list.

    Parameters
    ----------
    structure: .Structure
        Input structure to apply strain to
    deformations: list[.Deformation]
        A list of deformations to apply **independently** to the input
        structure, in anticipation of performing an EOS fit.
        Deformations should be of the form of a 3x3 matrix, e.g.,
        [[1.2, 0., 0.], [0., 1.2, 0.], [0., 0., 1.2]]

        or::

        ((1.2, 0., 0.), (0., 1.2, 0.), (0., 0., 1.2))

    Returns
    -------
    list
        A list of .TransformedStructure objects corresponding to the
        list of input deformations.
    """
    transformations = []
    for deformation in deformations:
        ts = TransformedStructure(
            structure,
            transformations=[DeformStructureTransformation(deformation=deformation)],
        )
        transformations += [ts]
    return transformations


class MPMorphPVPostProcess(PostProcessEosPressure):

    def eval(self) -> None:
        """Fit the input data to the Birch-Murnaghan pressure EOS."""
        initial_pars = self._initial_fit()
        for jobtype in self._use_job_types:
            eos_params, ierr = leastsq(
                self._objective, initial_pars[jobtype], args=(jobtype,)
            )
            self.results[jobtype]["EOS"] = {}
            if ierr not in (1, 2, 3, 4):
                self.results[jobtype]["EOS"]["exception"] = (
                    "Optimal EOS parameters not found."
                )
            else:
                for i, key in enumerate(["b0", "b1", "v0"]):
                    self.results[jobtype]["EOS"][key] = eos_params[i]

        self.results["V0"] = self.results[jobtype]["EOS"].get("v0")
        self.results["Vmax"] = max(self.results["relax"]["volume"])
        self.results["Vmin"] = min(self.results["relax"]["volume"])


class MPMorphEVPostProcess(PostProcessEosEnergy):

    eos_models: tuple[str, ...] = (
        "vinet",
        "birch_murnaghan",
        "birch",
        "pourier_tarantola",
        "murnaghan",
    )

    def eval(self) -> None:
        """Fit the input data to the Birch-Murnaghan pressure EOS."""
        for jobtype in self._use_job_types:
            self.results[jobtype]["EOS"] = {}
            for eos_name in self.eos_models:
                try:
                    eos = EOS(eos_name=eos_name).fit(
                        self.results[jobtype]["volume"], self.results[jobtype]["energy"]
                    )
                    self.results[jobtype]["EOS"][eos_name] = {
                        **eos.results,
                        "b0 GPa": float(eos.b0_GPa),
                    }
                except EOSError as exc:
                    self.results[jobtype]["EOS"][eos_name] = {"exception": str(exc)}

        for eos_func in self.eos_models:
            if v0 := self.results[jobtype]["EOS"][eos_func].get("v0"):
                self.results["V0"] = v0
                break

        self.results["Vmax"] = max(self.results["relax"]["volume"])
        self.results["Vmin"] = min(self.results["relax"]["volume"])
