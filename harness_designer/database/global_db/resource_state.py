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

from .bases import EntryBase, TableBase, DefaultStoredValue, DefaultStoredValueType
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
    _resources.RESOURCE_TYPE_MODEL: 'model3d_id'
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

    _stored_image_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def image_id(self) -> int | None:
        if self._stored_image_id is DefaultStoredValue:
            self._stored_image_id = self._table.select('image_id', id=self._db_id)[0][0]

        return self._stored_image_id

    _stored_datasheet_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def datasheet_id(self) -> int | None:
        if self._stored_datasheet_id is DefaultStoredValue:
            self._stored_datasheet_id = self._table.select('datasheet_id', id=self._db_id)[0][0]

        return self._stored_datasheet_id

    _stored_cad_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def cad_id(self) -> int | None:
        if self._stored_cad_id is DefaultStoredValue:
            self._stored_cad_id = self._table.select('cad_id', id=self._db_id)[0][0]

        return self._stored_cad_id

    _stored_model3d_id: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def model3d_id(self) -> int | None:
        if self._stored_model3d_id is DefaultStoredValue:
            self._stored_model3d_id = self._table.select('model3d_id', id=self._db_id)[0][0]

        return self._stored_model3d_id

    _stored_progress: DefaultStoredValueType | int = DefaultStoredValue

    @property
    def progress(self) -> int:
        if self._stored_progress is DefaultStoredValue:
            self._stored_progress = self._table.select('progress', id=self._db_id)[0][0]

        return self._stored_progress

    @progress.setter
    def progress(self, value: int):
        if value == 0 and self.claimed_by_host is None:
            self.claimed_by_host = _hostname()
            self.claimed_at = _now_iso()

        self._stored_progress = value
        self._table.update(self._db_id, progress=value)

    _stored_claimed_by_host: DefaultStoredValueType | str | None = DefaultStoredValue

    @property
    def claimed_by_host(self) -> str | None:
        if self._stored_claimed_by_host is DefaultStoredValue:
            self._stored_claimed_by_host = self._table.select('claimed_by_host', id=self._db_id)[0][0]

        return self._stored_claimed_by_host

    @claimed_by_host.setter
    def claimed_by_host(self, value: str):
        self._stored_claimed_by_host = value
        self._table.update(self._db_id, claimed_by_host=value)

    _stored_claimed_at: DefaultStoredValueType | str | None = DefaultStoredValue

    @property
    def claimed_at(self) -> str | None:
        if self._stored_claimed_at is DefaultStoredValue:
            self._stored_claimed_at = self._table.select('claimed_at', id=self._db_id)[0][0]

        return self._stored_claimed_at

    @claimed_at.setter
    def claimed_at(self, value: str):
        self._stored_claimed_at = value
        self._table.update(self._db_id, claimed_at=value)

    _stored_updated_at: DefaultStoredValueType | str | None = DefaultStoredValue

    @property
    def updated_at(self) -> str | None:
        if self._stored_updated_at is DefaultStoredValue:
            self._stored_updated_at = self._table.select('updated_at', id=self._db_id)[0][0]

        return self._stored_updated_at

    @updated_at.setter
    def updated_at(self, value: str):
        self._stored_updated_at = value
        self._table.update(self._db_id, updated_at=value)

    def update_progress(self, step):
        self.progress = step
        self.updated_at = _now_iso()

    _stored_retry_count: DefaultStoredValueType | int = DefaultStoredValue

    @property
    def retry_count(self) -> int:
        if self._stored_retry_count is DefaultStoredValue:
            self._stored_retry_count = self._table.select('retry_count', id=self._db_id)[0][0]

        return self._stored_retry_count

    @retry_count.setter
    def retry_count(self, value: int):
        self._stored_retry_count = value
        self._table.update(self._db_id, retry_count=value)

    _stored_error_step: DefaultStoredValueType | int | None = DefaultStoredValue

    @property
    def error_step(self) -> int | None:
        if self._stored_error_step is DefaultStoredValue:
            self._stored_error_step = self._table.select('error_step', id=self._db_id)[0][0]

        return self._stored_error_step

    @error_step.setter
    def error_step(self, value: int | None):
        self._stored_error_step = value
        self._table.update(self._db_id, error_step=value)

    _stored_error_blob: DefaultStoredValueType | str | None = DefaultStoredValue

    @property
    def error_blob(self) -> str | None:
        if self._stored_error_blob is DefaultStoredValue:
            self._stored_error_blob = self._table.select('error_blob', id=self._db_id)[0][0]

        return self._stored_error_blob

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
        self._stored_error_blob = value
        self._table.update(self._db_id, error_blob=value)

    _stored_error_at: DefaultStoredValueType | str | None = DefaultStoredValue

    @property
    def error_at(self) -> str | None:
        if self._stored_error_at is DefaultStoredValue:
            self._stored_error_at = self._table.select('error_at', id=self._db_id)[0][0]

        return self._stored_error_at

    @error_at.setter
    def error_at(self, value: str):
        self._stored_error_at = value
        self._table.update(self._db_id, error_at=value)

    _stored_error_host: DefaultStoredValueType | str | None = DefaultStoredValue

    @property
    def error_host(self) -> str | None:
        if self._stored_error_host is DefaultStoredValue:
            self._stored_error_host = self._table.select('error_host', id=self._db_id)[0][0]

        return self._stored_error_host

    @error_host.setter
    def error_host(self, value: str):
        self._stored_error_host = value
        self._table.update(self._db_id, error_host=value)

    _stored_allow_retry: DefaultStoredValueType | bool = DefaultStoredValue

    @property
    def allow_retry(self) -> bool:
        if self._stored_allow_retry is DefaultStoredValue:
            self._stored_allow_retry = bool(self._table.select('allow_retry', id=self._db_id)[0][0])

        return self._stored_allow_retry

    @allow_retry.setter
    def allow_retry(self, value: bool):
        self._stored_allow_retry = value
        self._table.update(self._db_id, allow_retry=int(value))

