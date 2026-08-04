# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from PySide6.QtGui import QIcon

from . import base as _base
from ... import image as _image
from ... import check_types as _check_types
from ...database import id_generator as _id_generator


if TYPE_CHECKING:
    from ...database.global_db import wire as _wire


class WiresPage(_base.EditorList):
    _has_image = False
    _has_model_3d = False

    __table_name__ = 'wires'

    column_mapping = {
        0: ('DB ID', {'alias': 'id', 'field_name': 'id'}, True),
        1: ('Part Number', {'alias': 'part_number', 'field_name': 'part_number'}, True),
        2: ('Description', {'alias': 'description', 'field_name': 'description'}),
        3: ('Manufacturer', {'alias': 'mfg_name', 'field_name': 'mfg_id', 'ref_table': 'manufacturers', 'ref_field': 'name'}),
        4: ('Family', {'alias': 'family_name', 'field_name': 'family_id', 'ref_table': 'families', 'ref_field': 'name'}),
        5: ('Series', {'alias': 'series_name', 'field_name': 'series_id', 'ref_table': 'series', 'ref_field': 'name'}),
        6: ('Color', {'alias': 'color_name', 'field_name': 'color_id', 'ref_table': 'colors', 'ref_field': 'name'}),
        7: ('Temperature (min)', {'alias': 'min_temp_name', 'field_name': 'min_temp_id', 'ref_table': 'temperatures', 'ref_field': 'name'}),
        8: ('Temperature (max)', {'alias': 'max_temp_name', 'field_name': 'max_temp_id', 'ref_table': 'temperatures', 'ref_field': 'name'}),
        9: ('Jacket Material', {'alias': 'material_name', 'field_name': 'material_id', 'ref_table': 'materials', 'ref_field': 'name'}),
        10: ('Stripe Color', {'alias': 'stripe_color_name', 'field_name': 'stripe_color_id', 'ref_table': 'colors', 'ref_field': 'name'}),
        11: ('Core Material', {'alias': 'core_material_description', 'field_name': 'core_material_id', 'ref_table': 'platings', 'ref_field': 'description'}),
        12: ('Conductor Count', {'alias': 'num_conductors', 'field_name': 'num_conductors'}),
        13: ('Shielded', {'alias': 'shielded', 'field_name': 'shielded'}),
        14: ('TPI', {'alias': 'tpi', 'field_name': 'tpi'}),
        15: ('Wire Dia (mm)', {'alias': 'wire_size_dia', 'field_name': 'wire_size_dia'}),
        16: ('Wire Cross (mm²)', {'alias': 'wire_size_cross', 'field_name': 'wire_size_cross'}),
        17: ('Wire AWG', {'alias': 'wire_size_awg', 'field_name': 'wire_size_awg'}),
        18: ('Outside Dia (mm)', {'alias': 'od_mm', 'field_name': 'od_mm'}),
        19: ('Weight (g/km)', {'alias': 'weight_1km', 'field_name': 'weight_1km'}),
        20: ('Resistance (Ω/km)', {'alias': 'resistance_1km', 'field_name': 'resistance_1km'}),
        21: ('Volts (V)', {'alias': 'volts', 'field_name': 'volts'}),
        22: ('Strands', {'alias': 'strands', 'field_name': 'strands'}),
    }

    table: "_wire.WiresTable" = None

    @_check_types.do
    def _get_icon(self, row_id):
        """Return the wire-insulation swatch icon for *row_id*.

        Wires have no real stored photo (``_has_image`` is False), so this
        overrides the base class's ``images_table`` lookup with a swatch
        generated on demand via ``image.images.build_wire`` -- same
        ``bitmap_indexes`` cache, keyed by ``db_id``, that every other
        part type's real image already uses (see
        :meth:`EditorList._get_icon`), so it's invalidated the same way on
        filter/search changes and a row never scrolled into view never
        pays for image generation.

        ``build_wire`` only supports a single, unshielded conductor -- any
        other wire falls back to the ordinary "no image" placeholder.

        :param row_id: Identifier for the row.
        :type row_id: int
        :returns: Return value.
        :rtype: :class:`PySide6.QtGui.QIcon`
        """
        if row_id < 0:
            return None

        row = self.get_row(row_id)
        if row is None:
            return None

        db_id = row[1]

        if db_id in self.bitmap_indexes:
            return self.bitmap_indexes[db_id]

        # column_mapping 12/13 == num_conductors/shielded -> row[13]/row[14]
        num_conductors = row[13]
        shielded = row[14]

        if num_conductors != 1 or shielded:
            self.bitmap_indexes[db_id] = _base.EditorList._no_image
            return _base.EditorList._no_image

        color_id, stripe_color_id, core_material_id = self.table.select(
            'color_id', 'stripe_color_id', 'core_material_id', id=db_id)[0]

        nil_uuid = _id_generator.NIL_UUID.bytes
        colors_table = self.table.db.colors_table

        primary_color = None if color_id is None or color_id == nil_uuid else colors_table[color_id]
        stripe_color = None if stripe_color_id is None or stripe_color_id == nil_uuid else colors_table[stripe_color_id]

        if core_material_id is None or core_material_id == nil_uuid:
            conductor_color = None
        else:
            conductor_color = self.table.db.platings_table[core_material_id].color

        if primary_color is None or conductor_color is None:
            self.bitmap_indexes[db_id] = _base.EditorList._no_image
            return _base.EditorList._no_image

        image = _image.images.build_wire(primary_color, stripe_color, conductor_color)
        image = image.resize_keep_aspect(64, 64)

        icon = QIcon(image.pixmap)
        self.bitmap_indexes[db_id] = icon

        return icon
