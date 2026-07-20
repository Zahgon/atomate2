
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2.vasp.jobs.base import BaseVaspMaker
from atomate2.vasp.sets.eos import (
    EosSetGenerator,
    MPGGAEosRelaxSetGenerator,
    MPGGAEosStaticSetGenerator,
    MPLegacyEosRelaxSetGenerator,
    MPLegacyEosStaticSetGenerator,
    MPMetaGGAEosPreRelaxSetGenerator,
    MPMetaGGAEosRelaxSetGenerator,
    MPMetaGGAEosStaticSetGenerator,
)

if TYPE_CHECKING:
    from atomate2.vasp.sets.base import VaspInputGenerator


copy_wavecar = lambda: {"additional_vasp_files": ("WAVECAR",)}  # noqa: E731


@dataclass
class EosRelaxMaker(BaseVaspMaker):

    name: str = "EOS GGA relax"
    input_set_generator: VaspInputGenerator = field(default_factory=EosSetGenerator)
    copy_vasp_kwargs: dict = field(default_factory=copy_wavecar)


@dataclass
class MPLegacyEosRelaxMaker(BaseVaspMaker):

    name: str = "EOS MP legacy GGA relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=MPLegacyEosRelaxSetGenerator
    )
    copy_vasp_kwargs: dict = field(default_factory=copy_wavecar)


@dataclass
class MPLegacyEosStaticMaker(BaseVaspMaker):

    name: str = "EOS MP legacy GGA static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=MPLegacyEosStaticSetGenerator
    )
    copy_vasp_kwargs: dict = field(default_factory=copy_wavecar)


@dataclass
class MPGGAEosRelaxMaker(BaseVaspMaker):

    name: str = "EOS MP GGA relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=MPGGAEosRelaxSetGenerator
    )
    copy_vasp_kwargs: dict = field(default_factory=copy_wavecar)


@dataclass
class MPGGAEosStaticMaker(BaseVaspMaker):

    name: str = "EOS MP GGA static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=MPGGAEosStaticSetGenerator
    )
    copy_vasp_kwargs: dict = field(default_factory=copy_wavecar)


@dataclass
class MPMetaGGAEosPreRelaxMaker(BaseVaspMaker):

    name: str = "EOS MP meta-GGA pre-relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=MPMetaGGAEosPreRelaxSetGenerator
    )


@dataclass
class MPMetaGGAEosRelaxMaker(BaseVaspMaker):

    name: str = "EOS MP meta-GGA relax"
    input_set_generator: VaspInputGenerator = field(
        default_factory=MPMetaGGAEosRelaxSetGenerator
    )
    copy_vasp_kwargs: dict = field(default_factory=copy_wavecar)


@dataclass
class MPMetaGGAEosStaticMaker(BaseVaspMaker):

    name: str = "EOS MP meta-GGA static"
    input_set_generator: VaspInputGenerator = field(
        default_factory=MPMetaGGAEosStaticSetGenerator
    )
    copy_vasp_kwargs: dict = field(default_factory=copy_wavecar)
