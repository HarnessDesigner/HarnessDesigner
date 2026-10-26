# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

import os
import json

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
def add_file_type(con: "_connector_base.ConnectorBase", name: str, extension: str,
                  is_model: bool | int = 0, is_image: bool | int = 0,
                  is_datasheet: bool | int = 0, is_cad: bool | int = 0,
                  mimetype: str = '', commit: bool = True) -> bytes:

    """
    Add a file type.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param name: Name value.
    :type name: str

    :param extension: Value for ``extension``.
    :type extension: str

    :param is_model: Boolean flag for whether model.
    :type is_model: bool | int

    :param is_image: Boolean flag for whether model.
    :type is_image: bool | int

    :param is_datasheet: Boolean flag for whether model.
    :type is_datasheet: bool | int

    :param is_cad: Boolean flag for whether model.
    :type is_cad: bool | int

    :param mimetype: Value for ``mimetype``.
    :type mimetype: str

    :param commit: Value for ``commit``.
    :type commit: bool

    :returns: Return value. UNKNOWN details.
    :rtype: bytes
    """

    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO file_types (id, mimetype, extension, name, '
                'is_model, is_image, is_datasheet, is_cad) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, mimetype, extension, name, int(is_model),
                 int(is_image), int(is_datasheet), int(is_cad)))

    _logger.database(f'file type added "{extension}"')

    if commit:
        con.commit()
        return new_id


@_check_types.do
def get_file_type(con: "_connector_base.ConnectorBase",
                  extension: str | None = None,
                  mimetype: str | None = None) -> bytes | None:

    """
    Return the file type.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param extension: Value for ``extension``.
    :type extension: str | None

    :param mimetype: Value for ``mimetype``.
    :type mimetype: str | None

    :returns: Return value. UNKNOWN details.
    :rtype: bytes | None
    """

    if extension is None and mimetype is None:
        return None

    if extension is not None and mimetype is not None:
        con.execute('SELECT id FROM file_types WHERE extension=? AND mimetype=?;',
                    (extension, mimetype))

        res = con.fetchall()

        if res:
            return res[0][0]

        _logger.database(f'adding file type ("{extension}", "{mimetype}")')

        db_id = _id_generator.generate_global_row_id(con).bytes
        con.execute('INSERT INTO file_types (id, extension, mimetype) '
                    'VALUES (?, ?, ?);',
                    (db_id, extension, mimetype))

        con.commit()

        _logger.database(f'file type added "{extension}" = {db_id}')

        return db_id

    elif extension is not None:
        con.execute('SELECT id FROM file_types WHERE extension=?;',
                    (extension,))

        res = con.fetchall()

        if res:
            return res[0][0]

        _logger.database(f'adding file type ("{extension}")')

        db_id = _id_generator.generate_global_row_id(con).bytes

        con.execute('INSERT INTO file_types (id, extension) VALUES (?, ?);',
                    (db_id, extension))

        con.commit()

        _logger.database(f'file type added "{extension}" = {db_id}')

        return db_id

    elif mimetype is not None:
        con.execute('SELECT id FROM file_types WHERE mimetype=?;',
                    (mimetype,))

        res = con.fetchall()

        if res:
            return res[0][0]

        return None


id_field = _con.UUIDField('id', is_primary=True)

table = _con.SQLTable(
    'file_types',
    id_field,
    _con.TextField('extension', no_null=True),
    _con.TextField('name', default='""', no_null=True),
    _con.TextField('mimetype', default='""', no_null=True),
    _con.IntField('is_model', default='0', no_null=True),
    _con.IntField('is_image', default='0', no_null=True),
    _con.IntField('is_datasheet', default='0', no_null=True),
    _con.IntField('is_cad', default='0', no_null=True)
)
