# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import manufacturers as _manufacturers
from . import families as _families
from . import series as _series
from . import colors as _colors
from . import materials as _materials
from . import models3d as _models3d
from . import images as _images
from . import datasheets as _datasheets
from . import cads as _cads
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
def add_accessory(con: "_connector_base.ConnectorBase", part_number: str, mfg: str,
                  description: str | None = None, series: str | None = None,
                  family: str | None = None, color: str | None = None,
                  material: str | None = None, image: str | None = None,
                  datasheet: str | None = None, cad: str | None = None,
                  model3d: str | None = None, length: float = 0.0,
                  width: float = 0.0, height: float = 0.0, weight: float = 0.0,
                  commit: bool = True) -> bytes:

    """
    Add an accessory.

    :param con: Value for ``con``.
    :type con: _connector_base.ConnectorBase

    :param part_number: Value for ``part_number``.
    :type part_number: str

    :param mfg: Value for ``mfg``.
    :type mfg: str

    :param description: Value for ``description``.
    :type description: str | None

    :param series: Value for ``series``.
    :type series: str | None

    :param family: Value for ``family``.
    :type family: str | None

    :param color: Value for ``color``.
    :type color: str | None

    :param material: Value for ``material``.
    :type material: str | None

    :param image: Value for ``image``.
    :type image: str | None

    :param datasheet: Value for ``datasheet``.
    :type datasheet: str | None

    :param cad: Value for ``cad``.
    :type cad: str | None

    :param model3d: Value for ``model3d``.
    :type model3d: str | None

    :param length: Value for ``length``.
    :type length: float

    :param width: Value for ``width``.
    :type width: float

    :param height: Value for ``height``.
    :type height: float

    :param weight: Value for ``weight``.
    :type weight: float

    :param commit: Value for ``commit``.
    :type commit: bool

    :returns: Return value. Row ID of the added record.
    :rtype: bytes
    """

    if color is None:
        color = 'Dark Gray'

    mfg, family, series = _manufacturers.inspect_mfg_fam_series(mfg, family, series)

    mfg_id = _manufacturers.get_mfg_id(con, mfg)
    series_id = _series.get_series_id(con, series, mfg_id)
    family_id = _families.get_family_id(con, family, mfg_id)
    color_id = _colors.get_color_id(con, color)
    material_id = _materials.get_material_id(con, material)
    image_id = _images.get_image_id(con, image)
    cad_id = _cads.get_cad_id(con, cad)
    datasheet_id = _datasheets.get_datasheet_id(con, datasheet)
    model3d_id = _models3d.get_model3d_id(con, model3d)

    if not description:
        description = mfg
        if series:
            description += f' {series}'

        if family:
            description += f' {family}'

        if material:
            description += f' {material}'

        if color:
            description += f' {color}'

        description += ' Accessory'

    _logger.database(f'adding accessory {part_number}, {description}')
    new_id = _id_generator.generate_global_row_id(con).bytes
    con.execute('INSERT INTO accessories (id, part_number, description, '
                'mfg_id, family_id, series_id, color_id, material_id, image_id, '
                'datasheet_id, cad_id, model3d_id, length, width, height, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (new_id, part_number, description, mfg_id, family_id, series_id,
                 color_id, material_id, image_id, datasheet_id, cad_id, model3d_id,
                 length, width, height, weight))

    _logger.database(f'accessory added "{part_number}"')

    if commit:
        con.commit()
        return new_id


id_field = _con.UUIDField('id', is_primary=True)


table = _con.SQLTable(
    'accessories',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.UUIDField('mfg_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_manufacturers.table,
                                                     _manufacturers.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('family_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_families.table,
                                                     _families.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('series_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_series.table,
                                                     _series.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('color_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_colors.table,
                                                     _colors.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('material_id', default="X'00000000000000000000000000000000'", no_null=True,
                   references=_con.SQLFieldReference(_materials.table,
                                                     _materials.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('image_id', default='NULL',
                   references=_con.SQLFieldReference(_images.table,
                                                     _images.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('datasheet_id', default='NULL',
                   references=_con.SQLFieldReference(_datasheets.table,
                                                     _datasheets.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('cad_id', default='NULL',
                   references=_con.SQLFieldReference(_cads.table,
                                                     _cads.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.UUIDField('model3d_id', default='NULL',
                   references=_con.SQLFieldReference(_models3d.table,
                                                     _models3d.id_field,
                                                     on_update=_con.REFERENCE_NO_ACTION)),
    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)
