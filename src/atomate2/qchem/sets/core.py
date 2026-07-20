
from __future__ import annotations

import logging
from dataclasses import dataclass

from atomate2.qchem.sets.base import QCInputGenerator

logger = logging.getLogger(__name__)


@dataclass
class SinglePointSetGenerator(QCInputGenerator):

    job_type: str = "sp"
    scf_algorithm: str = "diis"
    basis_set: str = "def2-tzvppd"


@dataclass
class OptSetGenerator(QCInputGenerator):

    job_type: str = "opt"
    scf_algorithm: str = "diis"
    basis_set: str = "def2-tzvppd"


@dataclass
class TransitionStateSetGenerator(QCInputGenerator):

    job_type: str = "ts"
    scf_algorithm: str = "diis"
    basis_set: str = "def2-tzvppd"


@dataclass
class ForceSetGenerator(QCInputGenerator):

    job_type: str = "force"
    scf_algorithm: str = "diis"
    basis_set: str = "def2-tzvppd"


@dataclass
class FreqSetGenerator(QCInputGenerator):

    job_type: str = "freq"
    scf_algorithm: str = "diis"
    basis_set: str = "def2-tzvppd"


@dataclass
class PESScanSetGenerator(QCInputGenerator):

    job_type: str = "pes_scan"
    scf_algorithm: str = "diis"
    basis_set: str = "def2-tzvppd"
