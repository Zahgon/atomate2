
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from glob import glob
from os import mkdir
from pathlib import Path
from typing import TYPE_CHECKING

from emmet.core.neb import NebIntermediateImagesDoc, NebTaskDoc
from jobflow import Flow, Maker, Response, job
from monty.serialization import dumpfn
from pymatgen.io.vasp import Kpoints

from atomate2 import SETTINGS
from atomate2.common.files import gzip_output_folder
from atomate2.common.jobs.neb import NebInterpolation, get_images_from_endpoints
from atomate2.utils.path import strip_hostname
from atomate2.vasp.files import copy_vasp_outputs, write_vasp_input_set
from atomate2.vasp.jobs.base import (
    _DATA_OBJECTS,
    _FILES_TO_ZIP,
    BaseVaspMaker,
    get_vasp_task_document,
)
from atomate2.vasp.run import JobType, run_vasp, should_stop_children
from atomate2.vasp.sets.core import NebSetGenerator

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pymatgen.core import Structure

    from atomate2.vasp.sets.base import VaspInputGenerator

logger = logging.getLogger(__name__)


def vasp_neb_job(method: Callable) -> job:
    pass


@job
def collect_neb_output(
    endpoint_dirs: list[str | Path] | None, neb_head_dir: str | Path, **neb_doc_kwargs
) -> NebTaskDoc:
    """Parse NEB output from image and optionally endpoint relaxations."""
    if endpoint_dirs is not None and len(endpoint_dirs) == 2:
        return NebTaskDoc.from_directories(
            [strip_hostname(endpoint_path) for endpoint_path in endpoint_dirs],
            strip_hostname(neb_head_dir),
            **neb_doc_kwargs,
        )
    return NebTaskDoc.from_directory(neb_head_dir, **neb_doc_kwargs)


@dataclass
class NebFromImagesMaker(BaseVaspMaker):

    name: str = "NEB"
    input_set_generator: VaspInputGenerator = field(default_factory=NebSetGenerator)
    run_vasp_kwargs: dict = field(
        default_factory=lambda: {
            "job_type": JobType.NEB,
            "vasp_job_kwargs": {
                "output_file": "vasp.out",
                "stderr_file": "std_err.txt",
            },
        }
    )
    kpoints_kludge: Kpoints | bool = True

    @vasp_neb_job
    def make(
        self,
        images: list[Structure],
        prev_dir: str | Path | None = None,
    ) -> Response:
        """
        Make an NEB job from a list of images.

        Parameters
        ----------
        images : list[Structure]
            A list of NEB images.
        prev_dir : str or Path or None (default)
            A previous directory to copy outputs from.

        """
        num_frames = len(images)
        num_images = num_frames - 2
        self.input_set_generator.num_images = num_images

        from_prev = prev_dir is not None
        if prev_dir is not None:
            copy_vasp_outputs(prev_dir, **self.copy_vasp_kwargs)

        self.write_input_set_kwargs.setdefault("from_prev", from_prev)

        write_vasp_input_set(
            images[0], self.input_set_generator, **self.write_input_set_kwargs
        )

        if (
            Path("KPOINTS").exists()
            and isinstance(self.kpoints_kludge, bool)
            and self.kpoints_kludge
        ):
            self.kpoints_kludge = Kpoints.from_file("KPOINTS")

        for iimage in range(num_frames):
            image_dir = f"{iimage:02}"
            mkdir(image_dir)

            images[iimage].to(f"{image_dir}/POSCAR")

            if isinstance(self.kpoints_kludge, Kpoints):
                self.kpoints_kludge.write_file(f"{image_dir}/KPOINTS")

        for filename, data in self.write_additional_data.items():
            dumpfn(data, filename.replace(":", "."))

        run_vasp(**self.run_vasp_kwargs)

        task_doc = get_vasp_task_document(
            Path.cwd(), is_neb=True, **self.task_document_kwargs
        )
        task_doc.task_label = self.name

        stop_children = should_stop_children(task_doc, **self.stop_children_kwargs)

        gzip_output_folder(
            directory=Path.cwd(),
            setting=SETTINGS.VASP_ZIP_FILES,
            files_list=_FILES_TO_ZIP,
        )

        for image_dir in glob(str(Path.cwd() / "[0-9][0-9]")):
            gzip_output_folder(
                directory=image_dir,
                setting=SETTINGS.VASP_ZIP_FILES,
                files_list=_FILES_TO_ZIP,
            )

        return Response(
            stop_children=stop_children,
            stored_data={"custodian": task_doc.custodian},
            output=task_doc,
        )


@dataclass
class NebFromEndpointsMaker(Maker):

    endpoint_relax_maker: BaseVaspMaker | None = None
    images_maker: NebFromImagesMaker = field(default_factory=NebFromImagesMaker)

    def make(
        self,
        endpoints: tuple[Structure, Structure] | list[Structure],
        num_images: int,
        prev_dir: str | Path = None,
        interpolation_method: NebInterpolation = NebInterpolation.LINEAR,
        **interpolation_kwargs,
    ) -> Flow:
        """
        Make an NEB job from a set of endpoints.

        Parameters
        ----------
        endpoints : tuple[Structure,Structure] or list[Structure]
            A set of two endpoints to interpolate NEB images from.
        num_images : int
            The number of images to include in the interpolation.
        prev_dir : str or Path or None (default)
            A previous directory to copy outputs from.
        interpolation_method : .NebInterpolation
            The method to use to interpolate between images.
        **interpolation_kwargs
            kwargs to pass to the interpolation function.
        """
        if len(endpoints) != 2:
            raise ValueError("Please specify exactly two endpoint structures.")

        endpoint_jobs = []
        endpoint_dirs: Sequence[str | Path] | None = None
        if self.endpoint_relax_maker is not None:
            endpoint_jobs += [
                self.endpoint_relax_maker.make(endpoint, prev_dir=prev_dir)
                for endpoint in endpoints
            ]
            for idx in range(2):
                endpoint_jobs[idx].append_name(f" endpoint {idx + 1}")
            endpoints = [relax_job.output.structure for relax_job in endpoint_jobs]
            endpoint_dirs = [
                endpoint_job.output.dir_name for endpoint_job in endpoint_jobs
            ]

        get_images = get_images_from_endpoints(
            endpoints,
            num_images,
            interpolation_method=interpolation_method,
            **interpolation_kwargs,
        )

        image_relax_job = self.images_maker.make(get_images.output)  # type: ignore[attr-defined]

        collate_job = collect_neb_output(
            endpoint_dirs, image_relax_job.output.dir_name, store_calculations=False
        )

        return Flow(
            [*endpoint_jobs, get_images, image_relax_job, collate_job],
            output=collate_job.output,
        )
