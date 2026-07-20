
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from atomate2.jdftx.jobs.base import BaseJdftxMaker
from atomate2.jdftx.sets.core import (
    IonicMinSetGenerator,
    LatticeMinSetGenerator,
    SinglePointSetGenerator,
)

if TYPE_CHECKING:
    from atomate2.jdftx.sets.base import JdftxInputGenerator


logger = logging.getLogger(__name__)


@dataclass
class SinglePointMaker(BaseJdftxMaker):

    name: str = "single_point"
    input_set_generator: JdftxInputGenerator = field(
        default_factory=SinglePointSetGenerator
    )


@dataclass
class IonicMinMaker(BaseJdftxMaker):

    name: str = "ionic_min"
    input_set_generator: JdftxInputGenerator = field(
        default_factory=IonicMinSetGenerator
    )


@dataclass
class LatticeMinMaker(BaseJdftxMaker):

    name: str = "lattice_min"
    input_set_generator: JdftxInputGenerator = field(
        default_factory=LatticeMinSetGenerator
    )
