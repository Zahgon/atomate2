
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from atomate2.jdftx.sets.base import _BASE_JDFTX_SET, JdftxInputGenerator

logger = logging.getLogger(__name__)


@dataclass
class SinglePointSetGenerator(JdftxInputGenerator):

    default_settings: dict = field(
        default_factory=lambda: {
            **_BASE_JDFTX_SET,
        }
    )


@dataclass
class IonicMinSetGenerator(JdftxInputGenerator):

    default_settings: dict = field(
        default_factory=lambda: {
            **_BASE_JDFTX_SET,
            "ionic-minimize": {"nIterations": 100},
        }
    )


@dataclass
class LatticeMinSetGenerator(JdftxInputGenerator):

    default_settings: dict = field(
        default_factory=lambda: {
            **_BASE_JDFTX_SET,
            "lattice-minimize": {"nIterations": 100},
            "latt-move-scale": {"s0": 1, "s1": 1, "s2": 1},
        }
    )


class BEASTSetGenerator(JdftxInputGenerator):

    default_settings: dict = field(
        default_factory=lambda: {
            **_BASE_JDFTX_SET,
            "fluid": {"type": "LinearPCM"},
            "pcm-variant": "CANDLE",
            "fluid-solvent": {"name": "H2O"},
            "fluid-cation": {"name": "Na+", "concentration": 0.5},
            "fluid-anion": {"name": "F-", "concentration": 0.5},
            "ionic-minimize": {"nIterations": 100},
        }
    )
