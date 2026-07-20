
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2.common.flows.eos import CommonEosMaker
from atomate2.vasp.flows.core import DoubleRelaxMaker
from atomate2.vasp.jobs.eos import (
    EosRelaxMaker,
    MPGGAEosRelaxMaker,
    MPGGAEosStaticMaker,
    MPLegacyEosRelaxMaker,
    MPLegacyEosStaticMaker,
    MPMetaGGAEosPreRelaxMaker,
    MPMetaGGAEosRelaxMaker,
    MPMetaGGAEosStaticMaker,
)
from atomate2.vasp.sets.eos import (
    EosSetGenerator,
    MPGGAEosRelaxSetGenerator,
    MPLegacyEosRelaxSetGenerator,
    MPMetaGGAEosRelaxSetGenerator,
)

if TYPE_CHECKING:
    from jobflow import Maker

    from atomate2.vasp.jobs.base import BaseVaspMaker



@dataclass
class EosDoubleRelaxMaker(DoubleRelaxMaker):

    name: str = "EOS double relax"
    relax_maker1: BaseVaspMaker | None = field(default_factory=EosRelaxMaker)
    relax_maker2: BaseVaspMaker = field(default_factory=EosRelaxMaker)


@dataclass
class EosMaker(CommonEosMaker):

    name: str = "EOS Maker"
    initial_relax_maker: Maker = field(default_factory=EosDoubleRelaxMaker)
    eos_relax_maker: Maker | None = field(
        default_factory=lambda: EosRelaxMaker(
            input_set_generator=EosSetGenerator(
                user_incar_settings={"ISIF": 2},
            )
        )
    )




@dataclass
class MPLegacyEosDoubleRelaxMaker(DoubleRelaxMaker):

    name: str = "MP Legacy EOS double relax"
    relax_maker1: BaseVaspMaker | None = field(default_factory=MPLegacyEosRelaxMaker)
    relax_maker2: BaseVaspMaker = field(default_factory=MPLegacyEosRelaxMaker)


@dataclass
class MPLegacyEosMaker(CommonEosMaker):

    name: str = "MP Legacy GGA EOS Maker"
    initial_relax_maker: Maker | None = field(
        default_factory=MPLegacyEosDoubleRelaxMaker
    )
    eos_relax_maker: Maker | None = field(
        default_factory=lambda: MPLegacyEosRelaxMaker(
            input_set_generator=MPLegacyEosRelaxSetGenerator(
                user_incar_settings={"ISIF": 2},
            )
        )
    )
    static_maker: Maker | None = field(default_factory=MPLegacyEosStaticMaker)




@dataclass
class MPGGAEosDoubleRelaxMaker(DoubleRelaxMaker):

    name: str = "MP GGA EOS double relax"
    relax_maker1: BaseVaspMaker | None = field(
        default_factory=lambda: MPGGAEosRelaxMaker(
            input_set_generator=MPGGAEosRelaxSetGenerator(
                user_incar_settings={"EDIFFG": -0.05}
            )
        )
    )
    relax_maker2: BaseVaspMaker = field(default_factory=MPGGAEosRelaxMaker)


@dataclass
class MPGGAEosMaker(CommonEosMaker):

    name: str = "MP GGA EOS Maker"
    initial_relax_maker: Maker | None = field(default_factory=MPGGAEosDoubleRelaxMaker)
    eos_relax_maker: Maker | None = field(
        default_factory=lambda: MPGGAEosRelaxMaker(
            input_set_generator=MPGGAEosRelaxSetGenerator(
                user_incar_settings={"ISIF": 2}
            )
        )
    )
    static_maker: Maker | None = field(default_factory=MPGGAEosStaticMaker)


@dataclass
class MPMetaGGAEosDoubleRelaxMaker(DoubleRelaxMaker):

    name: str = "MP Meta-GGA EOS double relax"
    relax_maker1: BaseVaspMaker | None = field(
        default_factory=MPMetaGGAEosPreRelaxMaker
    )
    relax_maker2: BaseVaspMaker = field(default_factory=MPMetaGGAEosRelaxMaker)


@dataclass
class MPMetaGGAEosMaker(CommonEosMaker):

    name: str = "MP Meta-GGA EOS Maker"
    initial_relax_maker: Maker | None = field(
        default_factory=MPMetaGGAEosDoubleRelaxMaker
    )
    eos_relax_maker: Maker | None = field(
        default_factory=lambda: MPMetaGGAEosRelaxMaker(
            input_set_generator=MPMetaGGAEosRelaxSetGenerator(
                user_incar_settings={"ISIF": 2}
            )
        )
    )
    static_maker: Maker | None = field(default_factory=MPMetaGGAEosStaticMaker)
