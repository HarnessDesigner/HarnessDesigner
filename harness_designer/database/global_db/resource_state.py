# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Global-DB table class for ``resource_state``.

This module exposes :class:`ResourceStateTable` which creates/migrates the
``resource_state`` table and its composite unique index.

The coordination helper functions (``ensure_row``, ``try_claim``,
``update_progress``, ``release_claim``, ``persist_error``) are defined in
:mod:`harness_designer.database.create_database.resource_state` and can be
imported from there directly by any module that needs them (including child
process workers that use the simplified ``db_broker`` connector).
"""

from ..create_database import resource_state as _resource_state
from .bases import TableBase

# Re-export everything callers may need so they only have to import this module.
RESOURCE_TYPE_MODEL = _resource_state.RESOURCE_TYPE_MODEL
RESOURCE_TYPE_IMAGE = _resource_state.RESOURCE_TYPE_IMAGE
RESOURCE_TYPE_DATASHEET = _resource_state.RESOURCE_TYPE_DATASHEET
RESOURCE_TYPE_CAD = _resource_state.RESOURCE_TYPE_CAD

PROGRESS_IDLE = _resource_state.PROGRESS_IDLE
PROGRESS_CLAIMED = _resource_state.PROGRESS_CLAIMED

ensure_row = _resource_state.ensure_row
get_state = _resource_state.get_state
try_claim = _resource_state.try_claim
update_progress = _resource_state.update_progress
release_claim = _resource_state.release_claim
persist_error = _resource_state.persist_error


class ResourceStateTable(TableBase):
    """Manage the shared ``resource_state`` coordination table.

    One row per ``(resource_type, resource_id)`` pair tracks progress,
    claiming host, and the last error blob for multi-seat deduplication.
    """

    __table_name__ = 'resource_state'

    def _table_needs_update(self) -> bool:
        return _resource_state.table.is_ok(self)

    def _add_table_to_db(self, _) -> None:
        # Use the module-level helper so the composite unique index is also
        # created in the same call.
        _resource_state.add_to_db(self)

    def _update_table_in_db(self) -> None:
        _resource_state.table.update_fields(self)
        # Ensure the unique index exists after an incremental field update too.
        _resource_state._add_unique_index(self)

