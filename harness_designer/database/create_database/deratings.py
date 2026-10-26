# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""
Schema for the ``deratings`` table.

A manufacturer's derating table for one catalog part (a terminal, a wire or a
splice): how much current the part may carry under given conditions. One row
per row of that part's table, so a part with a four-row table has four rows
here. This is global catalog data, static for each part, not a per-project
table.

Exactly one of ``terminal_id`` / ``wire_id`` / ``splice_id`` is set on a row
(enforced in ``DeratingsTable.insert``, as the project tables' own
exactly-one-of columns are), and ``idx`` is the row's position within its
part's table. The conditions and the limit are the remaining columns, each
NULL when the manufacturer's table does not use it:

* ``ambient_temp_c`` -- the ambient temperature the row applies at.
* ``conductor_count`` -- the number of current-carrying conductors bundled
  together; a row with one is a bundling row, not an ambient row.
* ``max_amps`` -- the most current the part may carry under those conditions.
* ``derating_factor`` -- the fraction of the part's own rated current that it
  may carry under those conditions (a row needs ``max_amps`` or
  ``derating_factor``, enforced in ``DeratingsTable.insert``).

NEW 2026-10-24. Mirrored in the sibling ``harness_designer_database`` repo
(``builder/create_database/deratings.py``), which builds the shared catalog;
keep the two aligned. Nothing populates the table yet: there is no source
data for it.
"""

from typing import TYPE_CHECKING

from . import splices as _splices
from . import terminals as _terminals
from . import wires as _wires
from .. import db_connectors as _con
from ... import logger as _logger


if TYPE_CHECKING:
    from ..global_db import bases as _glb_bases


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'deratings',
    id_field,
    _con.UUIDField('terminal_id', default='NULL',
                   references=_con.SQLFieldReference(_terminals.table,
                                                     _terminals.id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('wire_id', default='NULL',
                   references=_con.SQLFieldReference(_wires.table,
                                                     _wires.id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('splice_id', default='NULL',
                   references=_con.SQLFieldReference(_splices.table,
                                                     _splices.id_field,
                                                     on_delete=_con.REFERENCE_NO_ACTION,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.IntField('idx', no_null=True),
    _con.FloatField('ambient_temp_c', default='NULL'),
    _con.IntField('conductor_count', default='NULL'),
    _con.FloatField('max_amps', default='NULL'),
    _con.FloatField('derating_factor', default='NULL')
)


def add_indexes(db_cursor: "_glb_bases.TableBase") -> None:
    """
    Index the three part columns, so a part's table is found without
    reading every row of the catalog's.

    Only SQLite needs it: a MySQL foreign key already indexes its column.
    ``IF NOT EXISTS`` makes it safe to run on every start, and it is skipped
    quietly where the database cannot be written to (the lookup is then a scan,
    which is slower but not wrong).

    :param db_cursor: The ``deratings`` table class.
    :type db_cursor: :class:`_glb_bases.TableBase`
    """

    if _con.Config.database.connector != _con.CONNECTOR_SQLITE:
        return

    try:
        for column in ('terminal_id', 'wire_id', 'splice_id'):
            db_cursor._con.execute(f'CREATE INDEX IF NOT EXISTS deratings_{column}_index ON deratings ({column});')

        db_cursor._con.commit()
    except Exception as exc:  # NOQA
        _logger.database(f'could not index the deratings table: {exc!r}')
