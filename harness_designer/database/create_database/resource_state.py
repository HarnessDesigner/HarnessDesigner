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

import json
import socket
import datetime

from .. import db_connectors as _con
from ... import logger as _logger

# ---------------------------------------------------------------------------
# Resource-type constants – one symbol per domain table
# ---------------------------------------------------------------------------

RESOURCE_TYPE_MODEL = 'model'
RESOURCE_TYPE_IMAGE = 'image'
RESOURCE_TYPE_DATASHEET = 'datasheet'
RESOURCE_TYPE_CAD = 'cad'

# Progress sentinels
PROGRESS_IDLE = -1
PROGRESS_CLAIMED = 0

id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'resource_state',
    id_field,
    # Resource identity
    _con.TextField('resource_type', no_null=True),
    _con.IntField('resource_id', no_null=True),

    # Coordination / progress
    # -1 = idle, 0 = claimed, >0 = step progress
    _con.IntField('progress', default=str(PROGRESS_IDLE), no_null=True),
    _con.TextField('claimed_by_host', default='NULL'),
    _con.TextField('claimed_at', default='NULL'),
    _con.TextField('updated_at', default='NULL'),

    # Error / audit state
    _con.IntField('retry_count', default='0', no_null=True),
    _con.TextField('last_error_key', default='NULL'),
    _con.BlobField('last_error_blob', default='NULL'),
    _con.TextField('last_error_at', default='NULL'),
    _con.TextField('last_error_host', default='NULL'),

    # Non-retryable / blocking issue flag (e.g. watchdog timeout)
    _con.IntField('blocking_issue', default='0', no_null=True),
)


def add_to_db(db_cursor):
    """Create the ``resource_state`` table and its unique index.

    This must be called instead of ``table.add_to_db(db_cursor)`` directly so
    that the composite unique index on ``(resource_type, resource_id)`` is also
    created.

    :param db_cursor: Database cursor or connector wrapper used to execute SQL.
    :type db_cursor: UNKNOWN
    :returns: ``None``.
    :rtype: None
    """
    table.add_to_db(db_cursor)
    _add_unique_index(db_cursor)


def _add_unique_index(db_cursor):
    """Ensure the composite unique index exists on resource_state.

    Safe to call on new and existing databases – uses ``IF NOT EXISTS`` and
    swallows duplicate-data errors gracefully so that pre-existing databases
    are not hard-failed.

    .. note::
        ``db_cursor`` here is a :class:`TableBase` instance (passed from
        ``ResourceStateTable._add_table_to_db`` / ``_update_table_in_db``).
        Its ``._con`` attribute is the underlying SQL connector.  This matches
        the pattern used by :func:`sql_table.SQLTable.add_to_db` and is
        intentionally different from the child-process helpers below, which
        receive a raw connector directly.

    :param db_cursor: TableBase instance whose ``_con`` attribute exposes
        ``execute`` and ``commit``.
    :returns: ``None``.
    :rtype: None
    """
    sql = (
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_resource_state_unique '
        'ON resource_state (resource_type, resource_id);'
    )
    try:
        db_cursor._con.execute(sql)
        db_cursor._con.commit()
    except Exception as exc:
        _logger.logger.error(
            'resource_state: could not create unique index '
            '(existing duplicates?): ' + str(exc)
        )


# ---------------------------------------------------------------------------
# Low-level coordination helpers
#
# All functions accept a plain connector object that exposes at minimum:
#   connector.execute(sql_string)
#   connector.fetchall()
#   connector.commit()
#
# They deliberately avoid parameterised queries so that the simplified
# db_broker.BaseConnector used inside child processes is compatible.
#
# resource_type must be one of the RESOURCE_TYPE_* constants, and
# resource_id must be a plain integer.  Both are validated on entry to
# prevent accidental SQL injection from caller bugs.
# ---------------------------------------------------------------------------

_VALID_RESOURCE_TYPES = frozenset({
    RESOURCE_TYPE_MODEL,
    RESOURCE_TYPE_IMAGE,
    RESOURCE_TYPE_DATASHEET,
    RESOURCE_TYPE_CAD,
})


def _validate_args(resource_type: str, resource_id: int) -> None:
    """Raise ``ValueError`` for unexpected resource_type or resource_id.

    These values are embedded directly into SQL f-strings, so validating them
    here guards against accidental injection from caller bugs.

    :param resource_type: Must be one of the ``RESOURCE_TYPE_*`` constants.
    :param resource_id: Must be a non-negative integer.
    :raises ValueError: When either argument is outside the expected domain.
    """
    if resource_type not in _VALID_RESOURCE_TYPES:
        raise ValueError(f'resource_state: unexpected resource_type {resource_type!r}')
    if not isinstance(resource_id, int) or resource_id < 0:
        raise ValueError(f'resource_state: resource_id must be a non-negative int, got {resource_id!r}')

def _now_iso() -> str:
    """Return the current UTC timestamp as an ISO-8601 string."""
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')


def _hostname() -> str:
    """Return the short local hostname for this seat."""
    try:
        return socket.gethostname()
    except Exception:  # NOQA
        return 'unknown'


def ensure_row(connector, resource_type: str, resource_id: int) -> None:
    """Insert a resource-state row if one does not already exist.

    Uses ``INSERT OR IGNORE`` so concurrent seats cannot produce duplicates
    when the composite unique index is in place.

    :param connector: Database connector (main or child-process variant).
    :param resource_type: One of the ``RESOURCE_TYPE_*`` constants.
    :param resource_id: Primary-key value from the domain table.
    """
    _validate_args(resource_type, resource_id)
    connector.execute(
        f"INSERT OR IGNORE INTO resource_state "
        f"(resource_type, resource_id, progress, retry_count, blocking_issue) "
        f"VALUES ('{resource_type}', {resource_id}, {PROGRESS_IDLE}, 0, 0);"
    )
    connector.commit()


def get_state(connector, resource_type: str, resource_id: int) -> dict | None:
    """Return the current resource-state row as a dict, or ``None``.

    :param connector: Database connector.
    :param resource_type: Resource type constant.
    :param resource_id: Domain-table primary key.
    :returns: Dict with keys matching column names, or ``None`` when no row
        exists.
    :rtype: dict | None
    """
    _validate_args(resource_type, resource_id)
    connector.execute(
        f"SELECT progress, claimed_by_host, claimed_at, updated_at, "
        f"retry_count, last_error_key, last_error_at, last_error_host, "
        f"blocking_issue "
        f"FROM resource_state "
        f"WHERE resource_type='{resource_type}' AND resource_id={resource_id};"
    )
    rows = connector.fetchall()
    if not rows:
        return None

    row = rows[0]
    return {
        'progress': row[0],
        'claimed_by_host': row[1],
        'claimed_at': row[2],
        'updated_at': row[3],
        'retry_count': row[4],
        'last_error_key': row[5],
        'last_error_at': row[6],
        'last_error_host': row[7],
        'blocking_issue': row[8],
    }


def try_claim(connector, resource_type: str, resource_id: int) -> bool:
    """Attempt to claim a resource for processing on this seat.

    The claim is atomic from SQLite/MySQL's perspective: the ``UPDATE``
    only modifies the row when ``progress = -1 AND blocking_issue = 0``,
    so exactly one seat succeeds when multiple seats race.

    After the update, the row is re-read to confirm that *this* host is
    now the owner.

    :returns: ``True`` when this seat successfully claimed the resource.
    :rtype: bool
    """
    _validate_args(resource_type, resource_id)
    host = _hostname()
    now = _now_iso()

    connector.execute(
        f"UPDATE resource_state "
        f"SET progress={PROGRESS_CLAIMED}, "
        f"claimed_by_host='{host}', "
        f"claimed_at='{now}', "
        f"updated_at='{now}' "
        f"WHERE resource_type='{resource_type}' "
        f"AND resource_id={resource_id} "
        f"AND progress={PROGRESS_IDLE} "
        f"AND blocking_issue=0;"
    )
    connector.commit()

    state = get_state(connector, resource_type, resource_id)
    if state is None:
        return False

    return state.get('claimed_by_host') == host


def update_progress(connector, resource_type: str, resource_id: int,
                    step: int) -> None:
    """Advance the progress counter for a claimed resource.

    :param step: Positive integer representing the current pipeline step.
    """
    _validate_args(resource_type, resource_id)
    now = _now_iso()
    connector.execute(
        f"UPDATE resource_state "
        f"SET progress={step}, updated_at='{now}' "
        f"WHERE resource_type='{resource_type}' AND resource_id={resource_id};"
    )
    connector.commit()


def release_claim(connector, resource_type: str, resource_id: int) -> None:
    """Reset a claimed resource back to idle so it can be retried.

    Called after a recoverable error so another seat (or the same seat on
    restart) can pick up the work.
    """
    _validate_args(resource_type, resource_id)
    now = _now_iso()
    connector.execute(
        f"UPDATE resource_state "
        f"SET progress={PROGRESS_IDLE}, updated_at='{now}' "
        f"WHERE resource_type='{resource_type}' AND resource_id={resource_id};"
    )
    connector.commit()


def persist_error(connector, resource_type: str, resource_id: int,
                  error_key: str, error_blob: dict,
                  blocking: bool = False) -> None:
    """Persist error information for a resource and update retry bookkeeping.

    Error-identity rule:
    - If the same ``error_key`` is already stored, increment ``retry_count``.
    - If a different ``error_key`` is stored, overwrite the blob and reset
      ``retry_count`` to 0.

    Error data is **never cleared** on a later successful retry from another
    seat; it remains as an audit record of client-specific issues.

    :param error_key: Stable error identity string (requests error type or
        pipeline step name).  Must not include traceback path data.
    :param error_blob: Arbitrary dict with full diagnostics (message, etc.).
    :param blocking: When ``True`` the ``blocking_issue`` flag is set so no
        seat will auto-retry (e.g. after a watchdog timeout).
    """
    _validate_args(resource_type, resource_id)
    host = _hostname()
    now = _now_iso()

    state = get_state(connector, resource_type, resource_id)
    if state is None:
        return

    error_blob = dict(error_blob)
    error_blob['hostname'] = host
    error_blob['timestamp'] = now
    blob_json = json.dumps(error_blob, default=str)
    # Escape single-quotes for safe SQL string embedding
    blob_json_safe = blob_json.replace("'", "''")

    existing_key = state.get('last_error_key') or ''

    if existing_key == error_key:
        new_retry_count = (state.get('retry_count') or 0) + 1
    else:
        new_retry_count = 0

    blocking_val = 1 if blocking else 0
    error_key_safe = error_key.replace("'", "''")

    connector.execute(
        f"UPDATE resource_state "
        f"SET last_error_key='{error_key_safe}', "
        f"last_error_blob='{blob_json_safe}', "
        f"last_error_at='{now}', "
        f"last_error_host='{host}', "
        f"retry_count={new_retry_count}, "
        f"blocking_issue={blocking_val} "
        f"WHERE resource_type='{resource_type}' AND resource_id={resource_id};"
    )
    connector.commit()


