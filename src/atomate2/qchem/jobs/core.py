
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from atomate2.qchem.sets.base import QCInputGenerator

from atomate2.qchem.jobs.base import BaseQCMaker
from atomate2.qchem.sets.core import (
    ForceSetGenerator,
    FreqSetGenerator,
    OptSetGenerator,
    PESScanSetGenerator,
    SinglePointSetGenerator,
    TransitionStateSetGenerator,
)



logger = logging.getLogger(__name__)


@dataclass
class SinglePointMaker(BaseQCMaker):

    name: str = "single point"
    input_set_generator: QCInputGenerator = field(
        default_factory=SinglePointSetGenerator
    )


@dataclass
class OptMaker(BaseQCMaker):

    name: str = "optimization"
    input_set_generator: QCInputGenerator = field(default_factory=OptSetGenerator)


@dataclass
class ForceMaker(BaseQCMaker):

    name: str = "force"
    input_set_generator: QCInputGenerator = field(default_factory=ForceSetGenerator)


@dataclass
class TransitionStateMaker(BaseQCMaker):

    name: str = "transition state"
    input_set_generator: QCInputGenerator = field(
        default_factory=TransitionStateSetGenerator
    )


@dataclass
class FreqMaker(BaseQCMaker):

    name: str = "frequency"
    input_set_generator: QCInputGenerator = field(default_factory=FreqSetGenerator)
    task_type: str = "Frequency Analysis"


@dataclass
class PESScanMaker(BaseQCMaker):

    name: str = "PES scan"
    input_set_generator: QCInputGenerator = field(default_factory=PESScanSetGenerator)
