
from dataclasses import dataclass, field

from pymatgen.io.aims.sets.base import AimsInputGenerator
from pymatgen.io.aims.sets.core import SocketIOSetGenerator, StaticSetGenerator

from atomate2.aims.jobs.base import BaseAimsMaker
from atomate2.aims.jobs.core import SocketIOStaticMaker


@dataclass
class PhononDisplacementMaker(BaseAimsMaker):

    name: str = "phonon static aims"

    input_set_generator: AimsInputGenerator = field(
        default_factory=lambda: StaticSetGenerator(
            user_params={"compute_forces": True},
            user_kpoints_settings={"density": 5.0, "even": True},
        )
    )


@dataclass
class PhononDisplacementMakerSocket(SocketIOStaticMaker):

    name: str = "phonon static aims socket"

    input_set_generator: AimsInputGenerator = field(
        default_factory=lambda: SocketIOSetGenerator(
            user_params={"compute_forces": True},
            user_kpoints_settings={"density": 5.0, "even": True},
        )
    )
