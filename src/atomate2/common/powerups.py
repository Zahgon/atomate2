
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jobflow.core.flow import Flow
    from jobflow.core.maker import Maker


def add_metadata_to_flow(
    flow: Flow, additional_fields: dict, class_filter: type[Maker]
) -> Flow:
    pass


def update_custodian_handlers(
    flow: Flow, custom_handlers: tuple, class_filter: type[Maker]
) -> Flow:
    pass
