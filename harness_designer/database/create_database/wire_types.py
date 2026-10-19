# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash as _splash
    from ..db_connectors import base as _connector_base


@_check_types.do
def add_records(con: "_connector_base.ConnectorBase", splash: "_splash.Splash", _: str) -> None:
    """Add the default wire types when the table has none.

    The nil row, "Wire", is what a wire's ``wire_type_id`` defaults to, so a plain wire never needs a type set.

    :param con: Database connection.
    :param splash: Splash screen to report progress on.
    :param _: Unused data path.
    """
    con.execute('SELECT id FROM wire_types WHERE id=?;', (_id_generator.NIL_UUID.bytes,))
    if con.fetchall():
        return

    data = (
        dict(id=_id_generator.NIL_UUID.bytes, name='Wire'),
        dict(name='Coaxial'),
        dict(name='Ribbon'),
    )

    splash.SetText(f'Adding wire types to db [0 | {len(data)}]...')
    splash.flush()

    for i, item in enumerate(data):
        splash.SetText(f'Adding wire types to db [{i + 1} | {len(data)}]...')
        add_wire_type(con, commit=False, **item)

    con.commit()


@_check_types.do
def add_wire_type(con: "_connector_base.ConnectorBase", name: str, id: bytes | None = None, commit: bool = True) -> bytes | None:  # NOQA
    """Add a wire type.

    :param con: Database connection.
    :param name: Name of the wire type ("Wire", "Coaxial", "Ribbon", ...).
    :param id: Row id to use, the nil UUID for the default row; one is generated when it is ``None``.
    :param commit: Commit after the insert.
    :returns: The new row id when ``commit`` is true.
    """

    if id is None:
        id = _id_generator.generate_global_row_id(con).bytes

    con.execute(
        'INSERT INTO wire_types (id, name) '
        'VALUES (?, ?);', (id, name)
        )

    _logger.database(f'wire type added "{repr(name)}"')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_wire_type_id(con: "_connector_base.ConnectorBase", name: str | None) -> bytes:
    """Return the id of the wire type called ``name``, adding it when it does not exist.

    :param con: Database connection.
    :param name: Wire type name; blank or ``None`` is the default row ("Wire").
    :returns: The wire type row id.
    """
    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM wire_types WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding wire type ("{name}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO wire_types (id, name) VALUES (?, ?);', (db_id, name))

        con.commit()

        _logger.database(f'wire type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'wire_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
