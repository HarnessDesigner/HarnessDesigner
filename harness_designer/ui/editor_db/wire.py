# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


from PySide6 import QtGui

from . import base as _base
from ... import logger as _logger
from ... import check_types as _check_types
from ...database.global_db import wire_image as _wire_image
from ...image import wire_images as _wire_images


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
        23: ('Wire Type', {'alias': 'wire_type_name', 'field_name': 'wire_type_id', 'ref_table': 'wire_types', 'ref_field': 'name'}),
    }

    # What the picture of a wire needs besides the name columns above: the ids behind the colour and core columns, and
    # the cable's conductors (one text per conductor, ``idx,color,stripe,core`` as hex ids, joined with ``;``), all in the
    # same paged query. The list never makes a ``Wire`` row per line, which would also read that wire's conductors.
    _hidden_fields = ('color_id', 'stripe_color_id', 'core_material_id')
    _hidden_subselects = {
        'conductors': "SELECT group_concat(c.idx || ',' || hex(c.color_id) || ',' || hex(c.stripe_color_id) || ',' || "
                      "hex(c.core_material_id), ';') FROM wire_conductors AS c WHERE c.wire_id = paged.id"
    }

    table: "_wire.WiresTable" = None

    @_check_types.do
    def _image_row(self, row: tuple) -> "_wire_images.WireImageRow":
        """Return what the picture of the wire in ``row`` (a row of the paged query) is drawn from.

        :param row: A row from :meth:`get_row`.
        :type row: tuple
        :returns: The values :func:`images.build_wire` needs, without a ``Wire`` row.
        :rtype: :class:`WireImageRow`
        """
        columns = getattr(self, '_image_columns', None)

        if columns is None:
            # logical column -> alias, and a row has RowNum in front, so a column's index in the row is its logical number
            columns = {alias: index for index, alias in self.column_lookup.items()}
            self._image_columns = columns

        return _wire_images.WireImageRow.from_query(
            self.table.db,
            row[columns['wire_type_name']],
            row[columns['num_conductors']],
            row[self.hidden_index('color_id')],
            row[self.hidden_index('stripe_color_id')],
            row[self.hidden_index('core_material_id')],
            row[columns['shielded']],
            row[columns['tpi']],
            row[self.hidden_index('conductors')])

    @_check_types.do
    def _get_icon(self, row_id: int) -> QtGui.QIcon | None:
        """Return the wire-insulation swatch icon for *row_id*.

        Wires have no real stored photo (``_has_image`` is False), so this
        overrides the base class's ``images_table`` lookup with a swatch
        generated on demand by :func:`images.build_wire` -- same
        ``bitmap_indexes`` cache, keyed by ``db_id``, that every other
        part type's real image already uses (see
        :meth:`EditorList._get_icon`), so it's invalidated the same way on
        filter/search changes and a row never scrolled into view never
        pays for image generation.

        A single conductor, a twisted pair or triple, a jacketed and / or
        shielded cable and a coax cable each get their own picture; a wire
        that cannot be drawn (no conductor rows, ribbon, a missing colour)
        falls back to the ordinary "no image" placeholder.

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

        # which picture a wire gets (single wire, twisted pair / triple, jacketed cable, coax) is decided in one place
        # (wires that look the same share ONE icon object, so this row costs a reference, not a pixmap). It is drawn from
        # the values the list's own query returned, not from a ``Wire`` row.
        try:
            icon = _wire_image.build_wire_icon(self._image_row(row), 64)
        except Exception as exc:  # NOQA
            _logger.error(f'wire editor: could not build the image of a wire: {exc!r}')
            icon = None

        if icon is None:
            self.bitmap_indexes[db_id] = _base.EditorList._no_image
            return _base.EditorList._no_image

        self.bitmap_indexes[db_id] = icon

        return icon
