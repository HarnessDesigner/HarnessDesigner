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

from typing import Iterable as _Iterable

import json
import socket
import datetime

from .bases import EntryBase, TableBase
from ... import resources as _resources
from ..create_database import resource_state as _resource_state


def _hostname() -> str:
    """Return the short local hostname for this seat."""
    try:
        return socket.gethostname()
    except Exception:  # NOQA
        return 'unknown'


def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.datetime.now(
        datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


_TYPE_TO_FIELD = {
    _resources.RESOURCE_TYPE_CAD: 'cad_id',
    _resources.RESOURCE_TYPE_DATASHEET: 'datasheet_id',
    _resources.RESOURCE_TYPE_IMAGE: 'image_id',
    _resources.RESOURCE_TYPE_MODEL: 'model_id'
}


class ResourceStateTable(TableBase):
    """Manage the shared ``resource_state`` coordination table.

    One row per ``(resource_type, resource_id)`` pair tracks progress,
    claiming host, and the last error blob for multi-seat deduplication.
    """

    __table_name__ = 'resource_state'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        return _resource_state.table.is_ok(self)

    def _add_table_to_db(self, _):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        _resource_state.table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        _resource_state.table.update_fields(self)

    def __contains__(self, item: tuple[int, int]) -> bool:
        resource_type, resource_id = item
        field_name = _TYPE_TO_FIELD[resource_type]

        self.execute(f'SELECT id FROM {self.__table_name__} WHERE {field_name}={resource_id};')
        rows = self.fetchall()
        if rows:
            return True

        return False

    def __getitem__(self, item: tuple[int, int]) -> "ResourceState":
        resource_type, resource_id = item
        field_name = _TYPE_TO_FIELD[resource_type]

        self.execute(f'SELECT id FROM {self.__table_name__} WHERE {field_name}={resource_id};')
        rows = self.fetchall()

        if rows:
            db_id = rows[0][0]

            return ResourceState(self, db_id)

        raise KeyError('invalid resource id')

    def insert(self, resource_type, resource_id) -> "ResourceState":
        field_name = _TYPE_TO_FIELD[resource_type]

        kwargs = {field_name: resource_id}

        db_id = TableBase.insert(self, **kwargs)

        return ResourceState(self, db_id)


class ResourceState(EntryBase):

    _table: ResourceStateTable = None

    @property
    def image_id(self) -> int | None:
        return self._table.select('image_id', id=self._db_id)[0][0]

    @property
    def datasheet_id(self) -> int | None:
        return self._table.select('image_id', id=self._db_id)[0][0]

    @property
    def cad_id(self) -> int | None:
        return self._table.select('image_id', id=self._db_id)[0][0]

    @property
    def model3d_id(self) -> int | None:
        return self._table.select('image_id', id=self._db_id)[0][0]

    @property
    def progress(self) -> int:
        return self._table.select('progress', id=self._db_id)[0][0]

    @progress.setter
    def progress(self, value: int):
        if value == 0 and self.claimed_by_host is None:
            self.claimed_by_host = _hostname()
            self.claimed_at = _now_iso()

        self._table.update(self._db_id, progress=value)

    @property
    def claimed_by_host(self) -> str | None:
        return self._table.select('claimed_by_host', id=self._db_id)[0][0]

    @claimed_by_host.setter
    def claimed_by_host(self, value: str):
        self._table.update(self._db_id, claimed_by_host=value)

    @property
    def claimed_at(self) -> str | None:
        return self._table.select('claimed_at', id=self._db_id)[0][0]

    @claimed_at.setter
    def claimed_at(self, value: str):
        self._table.update(self._db_id, claimed_at=value)

    @property
    def updated_at(self) -> str | None:
        return self._table.select('updated_at', id=self._db_id)[0][0]

    @updated_at.setter
    def updated_at(self, value: str):
        self._table.update(self._db_id, updated_at=value)

    def update_progress(self, step):
        self.progress = step
        self.updated_at = _now_iso()

    @property
    def retry_count(self) -> int:
        return self._table.select('retry_count', id=self._db_id)[0][0]

    @retry_count.setter
    def retry_count(self, value: int):
        self._table.update(self._db_id, retry_count=value)

    @property
    def error_step(self) -> int | None:
        return self._table.select('error_step', id=self._db_id)[0][0]

    @error_step.setter
    def error_step(self, value: int | None):
        self._table.update(self._db_id, error_step=value)

    @property
    def error_blob(self) -> str | None:
        return self._table.select('error_blob', id=self._db_id)[0][0]

    def set_error(self, step, allow_retry, **error_blob):
        self.error_host = _hostname()
        self.error_at = _now_iso()
        self.allow_retry = allow_retry

        if self.error_step is None:
            self.error_step = step

        error_blob['step'] = step

        new_blob = json.dumps(error_blob)
        old_blob = self.error_blob

        if old_blob is None:
            self.error_blob = new_blob

        else:
            if new_blob != old_blob:
                self.error_blob = new_blob

            self.retry_count += 1

    @error_blob.setter
    def error_blob(self, value: str | None):
        self._table.update(self._db_id, error_blob=value)

    @property
    def error_at(self) -> str | None:
        return self._table.select('error_at', id=self._db_id)[0][0]

    @error_at.setter
    def error_at(self, value: str):
        self._table.update(self._db_id, error_at=value)

    @property
    def error_host(self) -> str | None:
        return self._table.select('error_host', id=self._db_id)[0][0]

    @error_host.setter
    def error_host(self, value: str):
        self._table.update(self._db_id, error_host=value)

    @property
    def allow_retry(self) -> bool:
        return bool(self._table.select('allow_retry', id=self._db_id)[0][0])

    @allow_retry.setter
    def allow_retry(self, value: bool):
        self._table.update(self._db_id, allow_retry=int(value))

