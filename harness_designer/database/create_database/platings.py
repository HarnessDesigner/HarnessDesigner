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
def add_plating(con: "_connector_base.ConnectorBase", symbol: str,  # NOQA
                description: str = '', id: int | None = None,  # NOQA
                commit: bool = True) -> bytes:  # NOQA

    """
    Add a plating.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param symbol: Value for ``symbol``.
    :type symbol: str

    :param description: Value for ``description``.
    :type description: str

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

    con.execute('INSERT INTO platings (id, symbol, description) '
                'VALUES (?, ?, ?);', (id_bytes, symbol, description))

    _logger.database(f'plating added "{symbol}" - "{description}"')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_plating_id(con: "_connector_base.ConnectorBase", symbol: str) -> bytes:
    """
    Return the plating ID.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param symbol: Value for ``symbol``.
    :type symbol: str

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    if not symbol:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM platings WHERE symbol=?;',
                (symbol,))

    rows = con.fetchall()

    if not rows:
        con.execute('SELECT id FROM platings WHERE description=?;',
                    (symbol,))

        rows = con.fetchall()

    if not rows:
        con.execute('SELECT symbol, description FROM platings;')
        rows = con.fetchall()

        items = {}

        platings = {row[1]: row[0] for row in rows}

        for key, value in platings.items():
            if key.lower() in symbol.lower():
                items[symbol.lower().find(key.lower())] = value

        if items:
            description = symbol
            symbol_parts = []
            for key in sorted(list(items.keys())):
                symbol_parts.append(items[key])

            symbol = '/'.join(symbol_parts)

            con.execute('SELECT id FROM platings WHERE symbol=?;',
                        (symbol,))

            rows = con.fetchall()

            if rows:
                return rows[0][0]

        else:
            description = ''

        _logger.database(f'adding plating ("{symbol}", "{description}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO platings (id, symbol, description) '
                    'VALUES (?, ?, ?);',
                    (db_id, symbol, description))

        con.commit()

        _logger.database(f'plating added "{symbol}" = {db_id}')

        return db_id
    else:
        return rows[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'platings',
    id_field,
    _con.TextField('symbol', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True)
)
