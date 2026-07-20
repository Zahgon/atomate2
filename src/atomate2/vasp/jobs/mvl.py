
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pymatgen.io.vasp.sets import MVLGWSet

from atomate2.vasp.jobs.base import BaseVaspMaker, vasp_job

if TYPE_CHECKING:
    from pathlib import Path

    from jobflow import Response
    from pymatgen.core.structure import Structure

    from atomate2.vasp.sets.base import VaspInputGenerator


logger = logging.getLogger(__name__)


@dataclass
class MVLStaticMaker(BaseVaspMaker):

    name: str = "MVL static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MVLGWSet(mode="STATIC")
    )

    @vasp_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> Response:
        """
        Run a static calculation compatible with later Materials Virtual Lab GW jobs.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.
        """
        return super().make.original(self, structure, prev_dir)


@dataclass
class MVLNonSCFMaker(BaseVaspMaker):

    name: str = "MVL nscf"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MVLGWSet(mode="DIAG")
    )

    @vasp_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> Response:
        """
        Run a static calculation compatible with later Materials Virtual Lab GW jobs.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.
        """
        self.copy_vasp_kwargs.setdefault("additional_vasp_files", ("CHGCAR",))

        return super().make.original(self, structure, prev_dir)


@dataclass
class MVLGWMaker(BaseVaspMaker):

    name: str = "MVL G0W0"
    input_set_generator: VaspInputGenerator = field(
        default_factory=lambda: MVLGWSet(mode="GW")
    )

    @vasp_job
    def make(
        self,
        structure: Structure,
        prev_dir: str | Path | None = None,
    ) -> Response:
        """
        Run a Materials Virtual Lab GW band structure VASP job.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.
        """
        self.copy_vasp_kwargs.setdefault(
            "additional_vasp_files", ("CHGCAR", "WAVECAR", "WAVEDER")
        )

        return super().make.original(self, structure, prev_dir)
