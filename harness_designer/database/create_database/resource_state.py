# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Schema and helpers for the shared resource coordination state table.

The ``resource_state`` table stores one row per (resource_type, resource_id) pair
and is the coordination hub that lets multiple seats avoid duplicate downloads or
conversions.

Progress semantics
------------------
``progress`` stores a small integer that carries the current job state:

* ``-1`` – idle / not yet queued
* ``0``  – claimed / queued (another seat is working on it)
* ``>0`` – in-progress step number reported by the worker
"""

from .. import db_connectors as _con
from ... import logger as _logger
from . import models3d as _models3d
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads

# ---------------------------------------------------------------------------
# Resource-type constants – one symbol per domain table
# ---------------------------------------------------------------------------

# Progress sentinels
PROGRESS_IDLE = -1
PROGRESS_CLAIMED = 0

id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'resource_state',
    id_field,
    _con.IntField('image_id', default='NULL',
                  references=_con.SQLFieldReference(_images.table,
                                                    _images.id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('datasheet_id', default='NULL',
                  references=_con.SQLFieldReference(_datasheets.table,
                                                    _datasheets.id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cad_id', default='NULL',
                  references=_con.SQLFieldReference(_cads.table,
                                                    _cads.id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_models3d.table,
                                                    _models3d.id_field,
                                                    on_delete=_con.REFERENCE_CASCADE,
                                                    on_update=_con.REFERENCE_CASCADE)),
    # Coordination / progress
    # -1 = idle, 0 = claimed, >0 = step progress
    _con.IntField('progress', default=f'{PROGRESS_IDLE}', no_null=True),
    _con.TextField('claimed_by_host', default='NULL'),
    _con.TextField('claimed_at', default='NULL'),
    _con.TextField('updated_at', default='NULL'),

    # Error / audit state
    _con.IntField('retry_count', default='0', no_null=True),
    _con.IntField('error_step', default='NULL'),
    _con.BlobField('error_blob', default='NULL'),
    _con.TextField('error_at', default='NULL'),
    _con.TextField('error_host', default='NULL'),

    # Non-retryable / blocking issue flag (e.g. watchdog timeout)
    _con.IntField('allow_retry', default='1', no_null=True),
)
