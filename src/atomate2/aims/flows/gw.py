
from dataclasses import dataclass, field

from atomate2.aims.jobs.convergence import ConvergenceMaker
from atomate2.aims.jobs.core import GWMaker


@dataclass
class GWConvergenceMaker(ConvergenceMaker):

    name: str = "GW convergence"
    maker: GWMaker = field(default_factory=GWMaker)
    criterion_name: str = "bandgap"
    epsilon: float = 0.1
