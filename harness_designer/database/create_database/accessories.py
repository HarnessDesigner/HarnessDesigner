# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

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
    con.execute('SELECT id FROM accessories WHERE id=0;')
    if con.fetchall():
        return

    splash.SetText(f'Building accessories...')
    splash.flush()

    data = (
        (0, 'None', 'No Accessories', 0),
        (1, 'S1017-1.0X50', '1" x 50\' Polyamide Adhesive, -20 – 60 °C [-4 – 140 °F], Hot Melt Tape', 1),
        (2, 'S1030', 'Polyolefin Adhesive, -80 – 80 °C [-112 – 176 °F], Hot Melt Tape', 1),
        (3, 'S1030-TAPE-3/4X33FT', '3/4" x 33\' Polyolefin Adhesive, -80 – 80 °C [-112 – 176 °F], Hot Melt Tape', 1),
        (4, 'S1048-TAPE-1X100-FT', '1" x 100\' Thermoplastic Adhesive, -55 – 120 °C [-67 – 248 °F], Hot Melt Tape', 1),
        (5, 'S1048-TAPE-3/4X100-FT', '3/4" x 100\' Thermoplastic Adhesive, -55 – 120 °C [-67 – 248 °F], Hot Melt Tape', 1),
        (6, 'S1125-KIT-1', 'Dual Pack, 5 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (7, 'S1125-KIT-4', 'Dual Pack, 5 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (8, 'S1125-KIT-5', 'Dual Pack, 1 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (9, 'S1125-KIT-8', 'Dual Pack, 1 Packaging Quantity, 150 °C Temperature (Max), Epoxy Adhesives', 1),
        (10, 'S1125-APPLICATOR', 'Epoxy Adhesives Dispensing Gun', 1)
    )
    splash.SetText(f'Adding accessories to db [{len(data)} | {len(data)}]...', log=False)
    splash.flush()

    con.executemany('INSERT INTO accessories (id, part_number, description, mfg_id) VALUES(?, ?, ?, ?);', data)
    con.commit()


def add_accessory(con, part_number, mfg, description=None, series=None,
                  family=None, color=None, material=None, image=None,
                  datasheet=None, cad=None, model3d=None, length=0.0,
                  width=0.0, height=0.0, weight=0.0, commit=True):
    """Add an accessory.

    UNKNOWN details are inferred from the callable name and signature.

    :param con: Value for ``con``.
    :type con: UNKNOWN
    :param part_number: Value for ``part_number``.
    :type part_number: UNKNOWN
    :param mfg: Value for ``mfg``.
    :type mfg: UNKNOWN
    :param description: Value for ``description``.
    :type description: UNKNOWN
    :param series: Value for ``series``.
    :type series: UNKNOWN
    :param family: Value for ``family``.
    :type family: UNKNOWN
    :param color: Value for ``color``.
    :type color: UNKNOWN
    :param material: Value for ``material``.
    :type material: UNKNOWN
    :param image: Value for ``image``.
    :type image: UNKNOWN
    :param datasheet: Value for ``datasheet``.
    :type datasheet: UNKNOWN
    :param cad: Value for ``cad``.
    :type cad: UNKNOWN
    :param model3d: Value for ``model3d``.
    :type model3d: UNKNOWN
    :param length: Value for ``length``.
    :type length: UNKNOWN
    :param width: Value for ``width``.
    :type width: UNKNOWN
    :param height: Value for ``height``.
    :type height: UNKNOWN
    :param weight: Value for ``weight``.
    :type weight: UNKNOWN
    :param commit: Value for ``commit``.
    :type commit: UNKNOWN
    :returns: Return value. UNKNOWN details.
    :rtype: UNKNOWN
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
    con.execute('INSERT INTO accessories (part_number, description, mfg_id, '
                'family_id, series_id, color_id, material_id, image_id, '
                'datasheet_id, cad_id, model3d_id, length, width, height, weight) '
                'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);',
                (part_number, description, mfg_id, family_id, series_id, color_id,
                 material_id, image_id, datasheet_id, cad_id, model3d_id, length,
                 width, height, weight))

    _logger.database(f'accessory added "{part_number}"')

    if commit:
        con.commit()
        return con.lastrowid


id_field = _con.PrimaryKeyField('id')


table = _con.SQLTable(
    'accessories',
    id_field,
    _con.TextField('part_number', is_unique=True, no_null=True),
    _con.TextField('description', default='""', no_null=True),
    _con.IntField('mfg_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_manufacturers.table,
                                                    _manufacturers.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('family_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_families.table,
                                                    _families.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('series_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_series.table,
                                                    _series.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('color_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_colors.table,
                                                    _colors.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('material_id', default='0', no_null=True,
                  references=_con.SQLFieldReference(_materials.table,
                                                    _materials.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('image_id', default='NULL',
                  references=_con.SQLFieldReference(_images.table,
                                                    _images.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('datasheet_id', default='NULL',
                  references=_con.SQLFieldReference(_datasheets.table,
                                                    _datasheets.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('cad_id', default='NULL',
                  references=_con.SQLFieldReference(_cads.table,
                                                    _cads.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),
    _con.IntField('model3d_id', default='NULL',
                  references=_con.SQLFieldReference(_models3d.table,
                                                    _models3d.id_field,
                                                    on_update=_con.REFERENCE_CASCADE)),


    _con.FloatField('length', default='"0.0"', no_null=True),
    _con.FloatField('width', default='"0.0"', no_null=True),
    _con.FloatField('height', default='"0.0"', no_null=True),
    _con.FloatField('weight', default='"0.0"', no_null=True)
)
