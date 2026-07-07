# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from . import manufacturers as _manufacturers
from ... import logger as _logger


def add_records(con, splash, _):
    """Add a records.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param splash: Value for ``splash``.
    :type splash: UNKNOWN
    :param _: Value for ``_``.
    :type _: UNKNOWN
    """
    con.execute('SELECT id FROM series WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Adding series to db [1 | 1]...')
    splash.flush()

    con.execute('INSERT INTO series (id, name) VALUES(0, "No Series");')
    con.commit()


def get_series_id(con, name, mfg_id):
    """Return the series ID.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param name: Name value.
    :type name: UNKNOWN
    :param mfg_id: Identifier for the mfg.
    :type mfg_id: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """
    if not name:
        return 0

    con.execute(f'SELECT id FROM series WHERE name="{name}" AND mfg_id={mfg_id};')
    res = con.fetchall()

    if not res:
        _logger.database(f'adding series ("{name}")')

        con.execute('INSERT INTO series (name, mfg_id) VALUES (?, ?);', (name, mfg_id))

        con.commit()
        db_id = con.lastrowid

        _logger.database(f'series added "{name}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.PrimaryKeyField('id')

table = _con.SQLTable(
    'series',
    id_field,
    _con.TextField('name', no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE))
)
