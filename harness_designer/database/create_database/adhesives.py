# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .. import db_connectors as _con
from ... import logger as _logger
from ... import check_types as _check_types
from .. import id_generator as _id_generator


@_check_types.do
def add_records(con, splash, _):
    """
    Add a records.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param splash: Value for ``splash``.
    :type splash: UNKNOWN

    :param _: Value for ``_``.
    :type _: UNKNOWN
    """

    con.execute('SELECT 1 FROM adhesives LIMIT 1;')
    if con.fetchall():
        return

    splash.SetText(f'Building adhesives...')
    splash.flush()

    codes = (
        ('None', 'No Adhesive', ''),
        ('225', 'Precoated latent-curing epoxy/polyamide', ''),
        ('42', 'Hot-melt/polyamide (Thermoplastic)', ''),
        ('86', 'Hot-melt,high performance (Thermoplastic)', ''),
        ('S1006', 'Epoxy/polyamide two-part paste (Thermoset)', ''),
        ('S1017', 'Hot-melt/polyamide (Thermoplastic)', 'S1017-1.0X50'),
        ('S1030', 'Hot-melt/polyolefin (Thermoplastic)', 'S1030, S1030-TAPE-3/4X33FT'),
        ('S1048', 'Hot-melt,high performance (Thermoplastic)', 'S1048-TAPE-1X100-FT, S1048-TAPE-3/4X100-FT'),
        ('S1125', 'Epoxy/polyamide two-part paste (Thermoset)', 'S1125-KIT-1, S1125-KIT-4, S1125-KIT-5, S1125-KIT-8, S1125-APPLICATOR')
    )

    data = tuple(
        (_id_generator.generate_global_row_id(con).bytes, code, description, accessory_part_nums)
        for code, description, accessory_part_nums in codes)

    splash.SetText(f'Adding adhesives to db [{len(data)} | {len(data)}]...', log=False)
    splash.flush()

    con.executemany('INSERT INTO adhesives (id, code, description, accessory_part_nums) VALUES (?, ?, ?, ?);', data)

    con.commit()


@_check_types.do
def get_adhesive_id(con, code):
    """
    Return the adhesive ID.

    :param con: Value for ``con``.
    :type con: UNKNOWN

    :param code: Value for ``code``.
    :type code: UNKNOWN

    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
    """

    if not code:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM adhesives WHERE code=?;', (code,))
    res = con.fetchall()

    if not res:
        _logger.database(f'adding adhesive ("{code}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO adhesives (id, code) VALUES (?, ?);', (db_id, code))

        con.commit()

        _logger.database(f'adhesive added "{code}" = {db_id}')

        return db_id
    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'adhesives',
    id_field,
    _con.TextField('code', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.TextField('accessory_part_nums', default='""', no_null=True)
)
