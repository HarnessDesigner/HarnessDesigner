# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Client-side generation of the 128-bit row-id scheme used by migrated tables.

One unified layout, used for both project_db and global_db rows --
global_db rows just carry ``project_id = 0`` (there's no project to scope
them to), so both kinds of id have the same fields at the same bit offsets::

    [ project_id : 24 ][ timestamp : 64 ][ reserved : 20 ][ version : 4 ][ user_id : 16 ]

``project_id`` (3 bytes) and ``user_id`` (2 bytes) both land on clean byte
boundaries deliberately -- ``project_id`` in particular needs to, since the
generated ``project_id`` column on migrated tables is a byte-slice
(``substr(id, 1, 3)``) rather than a bit-shifted extraction. The version tag
sits at a fixed bit offset, immediately before ``user_id`` -- keeping both
small "identity" fields together at the tail, easy to spot in a hex dump,
rather than version being buried behind a block of zeroedre served bits.
The reserved room can still grow into from either side (timestamp shrinking
its own headroom, or version/user_id needing more bits) without moving
version's own offset. Every field is
masked to its exact width before being combined, so the reserved bits are
zero by construction -- nothing is ever OR'd into them -- and a value that
doesn't actually fit its field raises instead of silently bleeding into a
neighboring field.

The timestamp component is never trusted for its raw clock resolution --
uniqueness comes from comparing each new reading against the last value
handed out and bumping forward by 1 on a tie *or* a backward clock jump,
never from randomness.

On MySQL this comparison happens inside a single GET_LOCK-serialized stored
function (``next_project_row_id``/``next_global_row_id``, see
db_connectors/mysql_connector), which also resolves the user id from
CURRENT_USER() server-side so it can't be spoofed by the client. On SQLite
(single-seat, single writer) the identical bump-on-tie/regression logic runs
here in Python instead, guarded by an in-process lock rather than a database
lock -- a local branch file has exactly one writer, so no cross-process
coordination is needed.
"""

import threading
import time
import uuid

from . import db_connectors as _con
from .. import config as _config
from .. import check_types as _check_types

Config = _config.Config.database

# Field widths, MSB to LSB. Must sum to 128.
_PROJECT_ID_BITS = 24
_TIMESTAMP_BITS = 64
_VERSION_BITS = 4
_RESERVED_BITS = 20
_USER_ID_BITS = 16

assert (_PROJECT_ID_BITS + _TIMESTAMP_BITS + _VERSION_BITS
        + _RESERVED_BITS + _USER_ID_BITS) == 128

# Bytes, not bits -- project_id and user_id are both required to land on
# byte boundaries (see module docstring), so this stays consistent by
# construction rather than by accident.
PROJECT_ID_BYTES = _PROJECT_ID_BITS // 8
USER_ID_BYTES = _USER_ID_BITS // 8

# Shift amounts, derived from the widths above rather than hardcoded, so the
# layout can only be changed in one place.
_USER_ID_SHIFT = 0
_VERSION_SHIFT = _USER_ID_SHIFT + _USER_ID_BITS
_RESERVED_SHIFT = _VERSION_SHIFT + _VERSION_BITS
_TIMESTAMP_SHIFT = _RESERVED_SHIFT + _RESERVED_BITS
_PROJECT_ID_SHIFT = _TIMESTAMP_SHIFT + _TIMESTAMP_BITS

_PROJECT_ID_MASK = (1 << _PROJECT_ID_BITS) - 1
_TIMESTAMP_MASK = (1 << _TIMESTAMP_BITS) - 1
_VERSION_MASK = (1 << _VERSION_BITS) - 1
_USER_ID_MASK = (1 << _USER_ID_BITS) - 1

# Bumped only if this bit layout itself ever changes again -- lets future
# code tell which packing scheme produced a given id without guessing.
FORMAT_VERSION = 1

# Placeholder user id for single-seat mode. Single-seat means exactly one
# user by definition, so there is no local identity system to resolve a real
# value from here -- populating this meaningfully belongs to whatever
# addon module eventually adds single-seat user identity, not this migration.
_LOCAL_USER_ID = 0


@_check_types.do
def _pack_row_id(project_id: int, timestamp_ns: int, user_id: int) -> bytes:
    """Pack a complete 16-byte row id.

    :param project_id: The owning project's existing integer id
        (``projects.id``), or ``0`` for a global_db row.
    :param timestamp_ns: Monotonic nanosecond timestamp component.
    :param user_id: ``app_users.id`` of the row's creator.

    :returns: The packed 16-byte row id.
    :rtype: bytes
    :raises ValueError: Raised when a field's value doesn't fit its
        allocated bit width.
    """
    if project_id & ~_PROJECT_ID_MASK:
        raise ValueError(f'project_id {project_id} does not fit in {_PROJECT_ID_BITS} bits')
    if timestamp_ns & ~_TIMESTAMP_MASK:
        raise ValueError(f'timestamp_ns {timestamp_ns} does not fit in {_TIMESTAMP_BITS} bits')
    if user_id & ~_USER_ID_MASK:
        raise ValueError(f'user_id {user_id} does not fit in {_USER_ID_BITS} bits')

    value = (
        ((project_id & _PROJECT_ID_MASK) << _PROJECT_ID_SHIFT)
        | ((timestamp_ns & _TIMESTAMP_MASK) << _TIMESTAMP_SHIFT)
        | ((FORMAT_VERSION & _VERSION_MASK) << _VERSION_SHIFT)
        | (user_id & _USER_ID_MASK)
    )
    return value.to_bytes(16, byteorder='big', signed=False)


@_check_types.do
def pack_project_row_id(project_id: int, timestamp_ns: int, user_id: int) -> bytes:
    """Pack a project_db child-table row id.

    :param project_id: The owning project's existing integer id (``projects.id``).
    :param timestamp_ns: Monotonic nanosecond timestamp component.
    :param user_id: ``app_users.id`` of the row's creator.

    :returns: The packed 16-byte row id.
    :rtype: bytes
    """
    return _pack_row_id(project_id, timestamp_ns, user_id)


@_check_types.do
def pack_global_row_id(timestamp_ns: int, user_id: int) -> bytes:
    """Pack a global_db row id -- same layout, ``project_id`` fixed at 0.

    :param timestamp_ns: Monotonic nanosecond timestamp component.
    :param user_id: ``app_users.id`` of the row's creator.

    :returns: The packed 16-byte row id.
    :rtype: bytes
    """
    return _pack_row_id(0, timestamp_ns, user_id)


@_check_types.do
def unpack_project_id(row_id: bytes) -> int:
    """Extract the project_id from a packed row id (0 for a global_db row).

    :param row_id: The packed 16-byte row id.

    :returns: The embedded project id.
    :rtype: int
    """
    value = int.from_bytes(row_id, byteorder='big', signed=False)
    return (value >> _PROJECT_ID_SHIFT) & _PROJECT_ID_MASK


@_check_types.do
def unpack_timestamp(row_id: bytes) -> int:
    """Extract the monotonic nanosecond timestamp from a packed row id.

    :param row_id: The packed 16-byte row id.

    :returns: The embedded timestamp.
    :rtype: int
    """
    value = int.from_bytes(row_id, byteorder='big', signed=False)
    return (value >> _TIMESTAMP_SHIFT) & _TIMESTAMP_MASK


@_check_types.do
def unpack_version(row_id: bytes) -> int:
    """Extract the format-version tag from a packed row id.

    :param row_id: The packed 16-byte row id.

    :returns: The embedded format version.
    :rtype: int
    """
    value = int.from_bytes(row_id, byteorder='big', signed=False)
    return (value >> _VERSION_SHIFT) & _VERSION_MASK


@_check_types.do
def unpack_user_id(row_id: bytes) -> int:
    """Extract the author's ``app_users.id`` from a packed row id.

    :param row_id: The packed 16-byte row id.

    :returns: The embedded user id.
    :rtype: int
    """
    value = int.from_bytes(row_id, byteorder='big', signed=False)
    return value & _USER_ID_MASK


class _LocalMonotonicClock:

    """Process-wide, lock-protected monotonic timestamp source.

    Used for single-seat (SQLite) row-id generation. Guards only against
    this process's own threads racing each other -- a local branch file has
    exactly one writer, so no cross-process/cross-machine coordination is
    required here the way the MySQL locked function needs it.
    """

    @_check_types.do
    def __init__(self):
        self._lock = threading.Lock()
        self._last_issued = 0

    @_check_types.do
    def next_timestamp(self) -> int:
        """Return a timestamp strictly greater than every value previously returned.

        :returns: A monotonic nanosecond timestamp.
        :rtype: int
        """
        with self._lock:
            now = time.time_ns()
            if now <= self._last_issued:
                now = self._last_issued + 1
            self._last_issued = now
            return now


_local_clock = _LocalMonotonicClock()


@_check_types.do
def generate_project_row_id(connector, project_id: int) -> uuid.UUID:
    """Generate a new row id for a project_db child-table row.

    :param connector: The active database connector.
    :param project_id: The owning project's existing integer id (``projects.id``).

    :returns: The newly generated row id.
    :rtype: uuid.UUID
    """
    if Config.connector == _con.CONNECTOR_MYSQL:
        connector.execute('SELECT next_project_row_id(?);', (project_id,))
        row_bytes = connector.fetchone()[0]
    else:
        timestamp_ns = _local_clock.next_timestamp()
        row_bytes = pack_project_row_id(project_id, timestamp_ns, _LOCAL_USER_ID)

    return uuid.UUID(bytes=row_bytes)


@_check_types.do
def generate_global_row_id(connector) -> uuid.UUID:
    """Generate a new row id for a global_db table row (no project scoping).

    :param connector: The active database connector.

    :returns: The newly generated row id.
    :rtype: uuid.UUID
    """
    if Config.connector == _con.CONNECTOR_MYSQL:
        connector.execute('SELECT next_global_row_id();')
        row_bytes = connector.fetchone()[0]
    else:
        timestamp_ns = _local_clock.next_timestamp()
        row_bytes = pack_global_row_id(timestamp_ns, _LOCAL_USER_ID)

    return uuid.UUID(bytes=row_bytes)


# The "unassigned" sentinel for a UUID foreign key -- matches every migrated
# table's own `default="X'00000000000000000000000000000000'"` DDL default
# (see db_connectors/*/sql_table.py's UUIDField). Real sentinel *rows* (e.g.
# "No Protection", "Unknown Material") are keyed on this id rather than a
# randomly generated one, so an FK column left at its schema default already
# points at the correct row with no lookup needed.
NIL_UUID = uuid.UUID(bytes=b'\x00' * 16)
