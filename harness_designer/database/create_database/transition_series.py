# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


if TYPE_CHECKING:
    from ... import splash_screen as _splash_screen
    from ..db_connectors import base as _connector_base


@_check_types.do
def add_records(con: "_connector_base.ConnectorBase",  # NOQA
                splash: "_splash_screen.Splash", _: str) -> None:  # NOQA

    """
    Add a records.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param splash: Value for ``splash``.
    :type splash: _splash_screen.Splash

    :param _: Value for ``_``.
    :type _: str
    """

    raise NotImplementedError


@_check_types.do
def get_transition_series_id(con: "_connector_base.ConnectorBase",
                             name: str) -> bytes:

    """
    Return the transition series ID.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param name: Name value.
    :type name: str

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM transition_series WHERE name=?;', (name,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding transition series ("{name}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO transition_series (id, name) VALUES (?, ?);', (db_id, name))

        con.commit()

        _logger.database(f'transition series added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'transition_series',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True)
)
