
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from jobflow import Flow, Maker
from pymatgen.io.vasp.sets import MatPESStaticSet

from atomate2.vasp.jobs.matpes import MatPesGGAStaticMaker, MatPesMetaGGAStaticMaker

if TYPE_CHECKING:
    from pathlib import Path

    from pymatgen.core import Structure


@dataclass
class MatPesStaticFlowMaker(Maker):

    name: str = "MatPES static flow"
    static1: Maker | None = field(
        default_factory=lambda: MatPesGGAStaticMaker(
            input_set_generator=MatPESStaticSet(
                user_incar_settings={"LWAVE": True}
            ),
        )
    )
    static2: Maker | None = field(
        default_factory=lambda: MatPesMetaGGAStaticMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR",)}
        )
    )
    static3: Maker | None = None

    def __post_init__(self) -> None:
        """Validate flow."""
        if (self.static1, self.static2, self.static3) == (None, None, None):
            raise ValueError("Must provide at least one StaticMaker")

    def make(self, structure: Structure, prev_dir: str | Path | None = None) -> Flow:
        """Create a flow with MatPES statics.

        By default, a PBE static is followed by an r2SCAN static and optionally a PBE+U
        static if the structure contains elements with +U corrections. The PBE static is
        run with LWAVE=True so its WAVECAR can be passed as a pre-conditioned starting
        point to both the r2SCAN static and the PBE+U static.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        prev_dir : str or Path or None
            A previous VASP calculation directory to copy output files from.

        Returns
        -------
        Flow
            A flow containing 2 or 3 statics.
        """
        jobs = []
        output = {}

        if self.static1 is not None:
            static1 = self.static1.make(structure, prev_dir=prev_dir)
            jobs += [static1]
            output["static1"] = static1.output

        prev_dir = static1.output.dir_name if self.static1 is not None else prev_dir

        if self.static2 is not None:
            static2 = self.static2.make(structure, prev_dir=prev_dir)
            jobs += [static2]
            output["static2"] = static2.output

        if self.static3 is not None:
            static3_config = self.static3.input_set_generator.config_dict
            u_corrections = static3_config.get("INCAR", {}).get("LDAUU", {})
            elems = set(map(str, structure.elements))
            if self.static3 and any(
                anion in elems and elems & {*cations}
                for anion, cations in u_corrections.items()
            ):
                static3 = self.static3.make(structure, prev_dir=prev_dir)
                output["static3"] = static3.output
                jobs += [static3]

        return Flow(jobs=jobs, output=output, name=self.name)
