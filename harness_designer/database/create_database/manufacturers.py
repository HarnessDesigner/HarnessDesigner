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
def inspect_mfg_fam_series(
    mfg_name: str,
    family_name: str | None,
    series_name: str | None
) -> tuple[str, str | None, str | None]:

    """
    Execute the inspect mfg fam series operation.

    :param mfg_name: Value for ``mfg_name``.
    :type mfg_name: str

    :param family_name: Value for ``family_name``.
    :type family_name: str | None

    :param series_name: Value for ``series_name``.
    :type series_name: str | None

    :returns: Return value. UNKNOWN details.
    :rtype: tuple[str, str | None, str | None]
    """

    if family_name is None:
        family_name = ''
    if series_name is None:
        series_name = ''

    if family_name.lower().startswith(mfg_name.lower()):
        family_name = family_name[len(mfg_name):]

    if series_name.lower().startswith(family_name.lower()):
        series_name = series_name[len(family_name):]

    if mfg_name in ('RAYCHEM', 'Raychem'):
        if not family_name.strip():
            family_name = 'Raychem'
        elif not series_name.strip():
            series_name = family_name.strip()
            family_name = 'Raychem'
        else:
            family_name = 'Raychem ' + family_name.strip()

        mfg_name = 'TE Connectivity'

    mfg_name = mfg_name.strip()
    family_name = family_name.strip()
    series_name = series_name.strip()

    if not family_name:
        family_name = None

    if not series_name:
        series_name = None

    return mfg_name, family_name, series_name


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
def add_manufacturer(con: "_connector_base.ConnectorBase", name: str,
                     description: str = '', address: str = '',
                     contact_person: str = '', phone: str = '', ext: str = '',
                     email: str = '', website: str = '', id: int | None = None,  # NOQA
                     commit: bool = True) -> bytes:

    """
    Add a manufacturer.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param name: Name value.
    :type name: str

    :param description: Value for ``description``.
    :type description: str

    :param address: Value for ``address``.
    :type address: str

    :param contact_person: Value for ``contact_person``.
    :type contact_person: str

    :param phone: Value for ``phone``.
    :type phone: str

    :param ext: Value for ``ext``.
    :type ext: str

    :param email: Value for ``email``.
    :type email: str

    :param website: Value for ``website``.
    :type website: str

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
        'INSERT INTO manufacturers (id, name, description, address, '
        'contact_person, phone, ext, email, website) '
        'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);',
        (id_bytes, name, description, address,
         contact_person, phone, ext, email, website)
        )

    _logger.database(f'manufacturer added "{name}"')

    if commit:
        con.commit()
        return id


@_check_types.do
def get_mfg_id(con: "_connector_base.ConnectorBase", name: str) -> bytes:
    """
    Return the mfg ID.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param name: Name value.
    :type name: str

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    if not name:
        return _id_generator.NIL_UUID.bytes

    con.execute('SELECT id FROM manufacturers WHERE name=?;',
                (name,))

    res = con.fetchall()

    if not res:
        _logger.database(f'adding manufacturer ("{name}", "", "", "", "")')
        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO manufacturers (id, name, phone, '
                    'address, email, website) '
                    'VALUES (?, ?, ?, ?, ?, ?);',
                    (db_id, name, '', '', '', ''))

        con.commit()
        _logger.database(f'manufacturer added "{name}" = {db_id}')

        return db_id

    else:
        return res[0][0]


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'manufacturers',
    id_field,
    _con.TextField('name', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.TextField('address', default='""', no_null=True),
    _con.TextField('contact_person', default='""', no_null=True),
    _con.TextField('phone', default='""', no_null=True),
    _con.TextField('ext', default='""', no_null=True),
    _con.TextField('email', default='""', no_null=True),
    _con.TextField('website', default='""', no_null=True)
)
