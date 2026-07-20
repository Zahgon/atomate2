
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2.common.flows.mpmorph import FastQuenchMaker, SlowQuenchMaker
from atomate2.vasp.jobs.md import MDMaker
from atomate2.vasp.jobs.mp import MPGGARelaxMaker, MPGGAStaticMaker
from atomate2.vasp.powerups import update_user_incar_settings
from atomate2.vasp.sets.mpmorph import MPMorphMDSetGenerator

if TYPE_CHECKING:
    from pathlib import Path

    from jobflow import Flow, Job
    from pymatgen.core import Structure

    from atomate2.vasp.jobs.base import BaseVaspMaker
    from atomate2.vasp.sets.base import VaspInputGenerator


@dataclass
class BaseMPMorphMDMaker(MDMaker):

    name: str = "MPMorph MD Maker"
    input_set_generator: VaspInputGenerator = field(
        default_factory=MPMorphMDSetGenerator
    )


@dataclass
class SlowQuenchVaspMaker(SlowQuenchMaker):

    name: str = "vasp slow quench"
    md_maker: BaseVaspMaker = field(default_factory=BaseMPMorphMDMaker)

    def call_md_maker(
        self,
        structure: Structure,
        temp: float | tuple[float, float],
        prev_dir: str | Path | None = None,
    ) -> Flow | Job:
        """Call the VASP MD maker.

        Parameters
        ----------
        structure : .Structure
            A pymatgen structure object.
        temp : float or tuple[float, float]
            The temperature in Kelvin.
        prev_dir : str or Path or None
            A previous calculation directory to copy output files from.

        Returns
        -------
        A slow quench .Flow or .Job
        """
        incar_updates = {
            "NSW": self.quench_n_steps,
            "TEBEG": temp[0] if isinstance(temp, tuple) else temp,
            "TEEND": temp[1] if isinstance(temp, tuple) else temp,
        }

        self.md_maker = update_user_incar_settings(
            flow=self.md_maker,
            incar_updates=incar_updates,
        )
        self.md_maker = self.md_maker.update_kwargs(
            update={"name": f"Vasp Slow Quench MD Maker {temp}K"}
        )
        return self.md_maker.make(structure=structure, prev_dir=prev_dir)


@dataclass
class FastQuenchVaspMaker(FastQuenchMaker):

    name: str = "Vasp fast quench"
    relax_maker: BaseVaspMaker = field(default_factory=MPGGARelaxMaker)
    relax_maker2: BaseVaspMaker = field(
        default_factory=lambda: MPGGARelaxMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR", "CHGCAR")}
        )
    )
    static_maker: BaseVaspMaker = field(
        default_factory=lambda: MPGGAStaticMaker(
            copy_vasp_kwargs={"additional_vasp_files": ("WAVECAR", "CHGCAR")}
        )
    )
