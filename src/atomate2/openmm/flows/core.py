
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from emmet.core.openmm import Calculation, OpenMMTaskDocument
from jobflow import Flow, Job, Maker, Response
from monty.json import MontyDecoder, MontyEncoder

from atomate2.openmm.jobs.base import openmm_job
from atomate2.openmm.jobs.core import NVTMaker, TempChangeMaker
from atomate2.openmm.utils import create_list_summing_to

if TYPE_CHECKING:
    from openff.interchange import Interchange

    from atomate2.openmm.interchange import OpenMMInterchange
    from atomate2.openmm.jobs.base import BaseOpenMMMaker


def _get_calcs_reversed(job: Job | Flow) -> list[Calculation | list]:
    """Unwrap a nested list of calcs from jobs or flows."""
    if isinstance(job, Flow):
        return [_get_calcs_reversed(sub_job) for sub_job in job.jobs]
    return job.output.calcs_reversed


def _flatten_calcs(nested_calcs: list) -> list[Calculation]:
    """Flattening nested calcs."""
    flattened = []
    for item in nested_calcs:
        if isinstance(item, list):
            flattened.extend(_flatten_calcs(item))
        else:
            flattened.append(item)
    return flattened


@openmm_job
def collect_outputs(
    prev_dir: str,
    tags: list[str] | None,
    job_uuids: list[str],
    calcs_reversed: list[Calculation | list],
    task_type: str,
) -> Response:
    """Reformat the output of the OpenMMFlowMaker into a OpenMMTaskDocument."""
    with open(Path(prev_dir) / "taskdoc.json") as file:
        task_dict = json.load(file, cls=MontyDecoder)
        task_doc = OpenMMTaskDocument.model_validate(task_dict)

    calcs = _flatten_calcs(calcs_reversed)
    calcs.reverse()
    task_doc.calcs_reversed = calcs
    task_doc.tags = tags
    task_doc.job_uuids = job_uuids
    task_doc.task_type = task_type

    with open(Path(task_doc.dir_name) / "taskdoc.json", "w") as file:
        json.dump(task_doc.model_dump(), file, cls=MontyEncoder)

    return Response(output=task_doc)


@dataclass
class OpenMMFlowMaker(Maker):

    name: str = "flexible"
    tags: list[str] = field(default_factory=list)
    makers: list[BaseOpenMMMaker | OpenMMFlowMaker] = field(default_factory=list)
    collect_outputs: bool = True
    final_task_type: str = "collect"

    def make(
        self,
        interchange: Interchange | OpenMMInterchange | str,
        prev_dir: str | None = None,
    ) -> Flow:
        """Run the production simulation using the provided Interchange object.

        Parameters
        ----------
        interchange : Interchange
            The Interchange object containing the system
            to simulate.
        prev_task : Optional[ClassicalMDTaskDocument]
            The directory of the previous task.
        output_dir : Optional[Union[str, Path]]
            The directory to write reporter files to.

        Returns
        -------
        Flow
            A Flow object containing the OpenMM jobs for the simulation.
        """
        if len(self.makers) == 0:
            raise ValueError("At least one maker must be included")

        jobs: list = []
        job_uuids: list = []
        calcs_reversed = []
        for maker in self.makers:
            job = maker.make(
                interchange=interchange,
                prev_dir=prev_dir,
            )
            interchange = job.output.interchange
            prev_dir = job.output.dir_name
            jobs.append(job)

            if isinstance(job, Flow):
                job_uuids.extend(job.job_uuids)
            else:
                job_uuids.append(job.uuid)
            calcs_reversed.append(_get_calcs_reversed(job))

        if self.collect_outputs:
            collect_job = collect_outputs(
                prev_dir,
                tags=self.tags or None,
                job_uuids=job_uuids,
                calcs_reversed=calcs_reversed,
                task_type=self.final_task_type,
            )
            jobs.append(collect_job)

            return Flow(
                jobs,
                output=collect_job.output,
            )
        return Flow(
            jobs,
            output=job.output,
        )

    @classmethod
    def anneal_flow(
        cls,
        name: str = "anneal",
        tags: list[str] | None = None,
        anneal_temp: int = 400,
        final_temp: int = 298,
        n_steps: int | tuple[int, int, int] = 1500000,
        temp_steps: int | tuple[int, int, int] | None = None,
        job_names: tuple[str, str, str] = ("raise temp", "hold temp", "lower temp"),
        **kwargs,
    ) -> OpenMMFlowMaker:
        pass
