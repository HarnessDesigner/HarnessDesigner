# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import json
import os

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


@_check_types.do
def add_records(con: "_connector_base.ConnectorBase",  # NOQA
                splash: "_splash_screen.Splash", data_path: str) -> None:  # NOQA

    """
    Add a records.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param splash: Value for ``splash``.
    :type splash: _splash_screen.Splash

    :param data_path: Value for ``data_path``.
    :type data_path: str
    """

    raise NotImplementedError


@_check_types.do
def add_splice_type(con: "_connector_base.ConnectorBase", name: str,  # NOQA
                    id: int | None = None, commit: bool = True) -> bytes:  # NOQA

    """
    Add a splice type.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param name: Name value.
    :type name: str

    :param id: ``0`` from the catalog JSON stores the nil UUID
               (the "none" row that unassigned foreign keys
               default to) instead of a generated id; ``None`` generates one.
    :type id: int | None

    :param commit: Value for ``commit``.
    :type commit: bool

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    if id is None:
        id_bytes = _id_generator.generate_global_row_id(con).bytes
    else:
        id_bytes = _id_generator.NIL_UUID.bytes

    con.execute(
        'INSERT INTO splice_types (id, name) '
        'VALUES (?, ?);', (id_bytes, name)
        )

    _logger.database(f'splice type added "{name}"')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_splice_type_id(con: "_connector_base.ConnectorBase", name: str) -> bytes:
    """
    Return the splice type ID.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param name: Name value.
    :type name: str

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM splice_types WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding splice type ("{name}")')

        db_id = _id_generator.generate_global_row_id(con).bytes

        con.execute('INSERT INTO splice_types (id, name) '
                    'VALUES (?, ?);',
                    (db_id, name))

        con.commit()

        _logger.database(f'splice type added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'splice_types',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
