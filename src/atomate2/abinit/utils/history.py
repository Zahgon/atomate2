
from __future__ import annotations

import collections
import logging
import os
import traceback
from typing import TYPE_CHECKING, Any

from monty.json import MontyDecoder, MSONable, jsanitize

from atomate2.abinit.utils.common import OUTDIR_NAME

if TYPE_CHECKING:
    from pathlib import Path

    from abipy.abio.inputs import AbinitInput
    from abipy.flowtk.events import AbinitEvent
    from abipy.flowtk.utils import Directory
    from jobflow import Flow, Job
    from typing_extensions import Self

logger = logging.getLogger(__name__)


class JobHistory(collections.deque, MSONable):

    def as_dict(self) -> dict:
        """Create dictionary representation of the history."""
        items = [i.as_dict() if hasattr(i, "as_dict") else i for i in self]

        return {
            "items": items,
            "@module": type(self).__module__,
            "@class": type(self).__name__,
        }

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """Create instance of the history from its dictionary representation."""
        dec = MontyDecoder()
        return cls([dec.process_decoded(i) for i in d["items"]])

    def log_initialization(
        self, job: Job | Flow, initialization_info: Any | None = None
    ) -> None:
        pass

    def log_corrections(self, corrections: Any | None) -> None:
        pass

    def log_restart(self) -> None:
        """Log that the job is restarted."""
        self.append(
            JobEvent(
                JobEvent.RESTART,
            )
        )

    def log_start(self, workdir: Path | str | Directory, start_time: Any) -> None:
        """Log that the job has started."""
        self.append(
            JobEvent(
                JobEvent.START,
                details={"workdir": workdir, "start_time": start_time},
            )
        )

    def log_end(self, workdir: Path | str | Directory) -> None:
        pass

    @property
    def num_restarts(self) -> int:
        pass

    @property
    def run_number(self) -> int:
        pass

    @property
    def prev_dir(self) -> str:
        pass

    @property
    def prev_outdir(self) -> str:
        pass

    @property
    def is_first_run(self) -> bool:
        pass

    def log_autoparal(self, optconf: Any) -> None:
        pass

    def log_unconverged(self) -> None:
        pass

    def log_finalized(self, final_input: AbinitInput | None = None) -> None:
        pass

    def log_converge_params(
        self, unconverged_params: dict, abiinput: AbinitInput
    ) -> None:
        pass

    def log_error(self, exc: Any) -> None:
        pass

    def log_abinit_stop(self, run_time: Any | None = None) -> None:
        pass

    def get_events_by_types(self, types: list | AbinitEvent) -> list:
        pass

    def get_total_run_time(self) -> Any:
        pass


class JobEvent(MSONable):

    INITIALIZED = "initialized"
    CORRECTIONS = "corrections"
    START = "start"
    END = "end"
    RESTART = "restart"
    AUTOPARAL = "autoparal"
    UNCONVERGED = "unconverged"
    FINALIZED = "finalized"
    UNCONVERGED_PARAMS = "unconverged parameters"
    ERROR = "error"
    ABINIT_STOP = "abinit stop"

    def __init__(self, event_type: AbinitEvent, details: Any | None = None) -> None:
        """Construct JobEvent object."""
        self.event_type = event_type
        self.details = details

    def as_dict(self) -> dict:
        """Create dictionary representation of the job event."""
        dct = {"event_type": self.event_type}
        if self.details:
            dct["details"] = jsanitize(self.details, strict=True)
        dct["@module"] = type(self).__module__
        dct["@class"] = type(self).__name__
        return dct

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        """Create instance of the job event from its dictionary representation."""
        dec = MontyDecoder()
        details = dec.process_decoded(d["details"]) if "details" in d else None
        return cls(event_type=d["event_type"], details=details)
