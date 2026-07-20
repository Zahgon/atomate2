
from __future__ import annotations

from copy import deepcopy
from typing import Any, TypeVar

from jobflow.core.flow import Flow
from jobflow.core.job import Job
from jobflow.core.maker import Maker
from pymatgen.io.vasp import Kpoints

from atomate2.common.powerups import add_metadata_to_flow as base_add_metadata_to_flow
from atomate2.common.powerups import update_custodian_handlers as base_custodian_handler
from atomate2.vasp.jobs.base import BaseVaspMaker

JobType = TypeVar("JobType", Job, Flow, Maker)
"""TypeVar for generic job, flow, or maker types. Used to ensure powerup functions
return the same type as their input."""


def update_vasp_input_generators(
    flow: JobType,
    dict_mod_updates: dict[str, Any],
    name_filter: str | None = None,
    class_filter: type[Maker] | None = BaseVaspMaker,
) -> JobType:
    """Update VaspInputGenerators or Makers in a job, flow, or maker.

    This function applies modifications to VASP input generators throughout a
    workflow. It creates a deep copy of the input, so the original remains unchanged.

    Parameters
    ----------
    flow : Job or Flow or Maker
        A job, flow, or maker to update.
    dict_mod_updates : dict[str, Any]
        Dictionary of updates to apply using arrow notation (e.g.,
        'input_set_generator->user_incar_settings->ENCUT'). Existing keys are
        preserved unless explicitly overridden.
    name_filter : str or None, optional
        Filter to apply updates only to jobs matching this name pattern.
        Default is None (no filtering).
    class_filter : type[Maker] or None, optional
        Filter to apply updates only to makers of this class or its subclasses.
        Default is BaseVaspMaker.

    Returns
    -------
    Job or Flow or Maker
        A deep copy of the input with updated VASP input generator settings.
    """
    updated_flow = deepcopy(flow)

    tmp_dict = {
        "update": {"_set": dict_mod_updates},
        "name_filter": name_filter,
        "class_filter": class_filter,
        "dict_mod": True,
    }

    if isinstance(updated_flow, Maker):
        updated_flow = updated_flow.update_kwargs(**tmp_dict)
    else:
        updated_flow.update_maker_kwargs(**tmp_dict)

    return updated_flow


def update_user_incar_settings(
    flow: JobType,
    incar_updates: dict[str, Any],
    name_filter: str | None = None,
    class_filter: type[Maker] | None = BaseVaspMaker,
) -> JobType:
    """Update user INCAR settings in VaspInputGenerators.

    Modifies the user_incar_settings attribute of VASP input generators within
    jobs, flows, or makers. Creates a copy of the input.

    Parameters
    ----------
    flow : Job or Flow or Maker
        A job, flow, or maker to update.
    incar_updates : dict[str, Any]
        Dictionary mapping INCAR tags to their new values (e.g.,
        {'ENCUT': 520, 'EDIFF': 1e-5}). Only specified keys are modified.
    name_filter : str or None, optional
        Filter to apply updates only to jobs matching this name pattern.
        Default is None (no filtering).
    class_filter : type[Maker] or None, optional
        Filter to apply updates only to makers of this class or its subclasses.
        Default is BaseVaspMaker.

    Returns
    -------
    Job or Flow or Maker
        A deep copy of the input with updated INCAR settings.

    Examples
    --------
    >>> flow = update_user_incar_settings(flow, {"ENCUT": 520, "ISMEAR": 0})
    """
    return update_vasp_input_generators(
        flow=flow,
        dict_mod_updates={
            f"input_set_generator->user_incar_settings->{k}": v
            for k, v in incar_updates.items()
        },
        name_filter=name_filter,
        class_filter=class_filter,
    )


def update_user_potcar_settings(
    flow: JobType,
    potcar_updates: dict[str, Any],
    name_filter: str | None = None,
    class_filter: type[Maker] | None = BaseVaspMaker,
) -> JobType:
    pass


def update_user_potcar_functional(
    flow: JobType,
    potcar_functional: str,
    name_filter: str | None = None,
    class_filter: type[Maker] | None = BaseVaspMaker,
) -> JobType:
    pass


def update_user_kpoints_settings(
    flow: JobType,
    kpoints_updates: dict[str, Any] | Kpoints,
    name_filter: str | None = None,
    class_filter: type[Maker] | None = BaseVaspMaker,
) -> JobType:
    """Update user k-points settings in VaspInputGenerators.

    Modifies the user_kpoints_settings attribute of VASP input generators within
    jobs, flows, or makers. Creates a copy of the input.

    Parameters
    ----------
    flow : Job or Flow or Maker
        A job, flow, or maker to update.
    kpoints_updates : dict[str, Any] or Kpoints
        K-points updates to apply. Can be either:
        - A dictionary with k-points settings (e.g., {'reciprocal_density': 100})
        - A Kpoints object that replaces the entire user_kpoints_settings
    name_filter : str or None, optional
        Filter to apply updates only to jobs matching this name pattern.
        Default is None (no filtering).
    class_filter : type[Maker] or None, optional
        Filter to apply updates only to makers of this class or its subclasses.
        Default is BaseVaspMaker.

    Returns
    -------
    Job or Flow or Maker
        A deep copy of the input with updated k-points settings.

    Examples
    --------
    >>> flow = update_user_kpoints_settings(flow, {"reciprocal_density": 200})
    >>> # Or with a Kpoints object
    >>> kpts = Kpoints.gamma_automatic((4, 4, 4))
    >>> flow = update_user_kpoints_settings(flow, kpts)
    """
    if isinstance(kpoints_updates, Kpoints):
        dict_mod_updates = {
            "input_set_generator->user_kpoints_settings": kpoints_updates
        }
    else:
        dict_mod_updates = {
            f"input_set_generator->user_kpoints_settings->{k}": v
            for k, v in kpoints_updates.items()
        }
    return update_vasp_input_generators(
        flow=flow,
        dict_mod_updates=dict_mod_updates,
        name_filter=name_filter,
        class_filter=class_filter,
    )


def use_auto_ispin(
    flow: JobType,
    value: bool = True,
    name_filter: str | None = None,
    class_filter: type[Maker] | None = BaseVaspMaker,
) -> JobType:
    pass


def add_metadata_to_flow(
    flow: Flow, additional_fields: dict, class_filter: type[Maker] = BaseVaspMaker
) -> Flow:
    pass


def update_vasp_custodian_handlers(
    flow: Flow, custom_handlers: tuple, class_filter: type[Maker] = BaseVaspMaker
) -> Flow:
    pass
