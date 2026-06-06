# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING


from PySide6.QtGui import QColor
from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin


if TYPE_CHECKING:
    from ...global_db import color as _color


class ColorMixin(BaseMixin):
    """Represent a color mixin in :mod:`harness_designer.database.global_db.mixins.color`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def color(self) -> "_color.Color":
        """Return the color.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_color.Color`
        """
        color_id = self._table.select('color_id', id=self._db_id)
        color = self._table.db.global_db.colors_table[color_id[0][0]]
        return color

    @property
    def color_id(self) -> int:
        """Return the color ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('color_id', id=self._db_id)[0][0]

    @color_id.setter
    def color_id(self, value: int):
        """Set the color ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, color_id=value)
        self._populate('color_id')


class ColorControl(_prop_ctrls.ColorProperty):
    """Represent a color control in :mod:`harness_designer.database.global_db.mixins.color`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`ColorControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.choices: list[list[str, int]] = None
        self.db_obj: ColorMixin = None
        self.attribute_name = 'color'

        super().__init__(parent, 'Color')

        self.property_changed.connect(self._on_color)

    def SetAttributeName(self, name):
        """Execute the set attribute name operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: UNKNOWN
        """
        self.attribute_name = name

    def set_obj(self, db_obj: ColorMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`ColorMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.SetItems(self.choices)
            self.SetValue(['', QColor(0, 0, 0)])
            self.Enable(False)
        else:
            color = getattr(db_obj, self.attribute_name)

            db_obj.table.execute('SELECT name, rgb from colors;')
            rows = db_obj.table.fetchall()
            self.choices = [list(row) for row in rows]

            self.SetItems(self.choices)
            self.SetValue([color.name, color.ui])
            self.Enable(True)

    def _on_color(self, evt):
        """Handle the color event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        name, color = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id, rgba FROM colors WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        r = color.GetRed()
        g = color.GetGreen()
        b = color.GetBlue()
        a = color.GetAlpha()

        rgba = r << 24 | g << 16 | b << 8 | a

        if rows:
            db_id, stored_rgba = rows[0]

            if rgba != stored_rgba:
                setattr(self.db_obj, self.attribute_name + '_id', db_id)
                getattr(self.db_obj, self.attribute_name).rgb = rgba
        else:
            db_obj = self.db_obj.table.db.colors_table.insert(name, rgba)
            db_id = db_obj.db_id

            self.choices.append([name, color])
            self.SetItems(self.choices)
            self.SetValue([name, color])

        setattr(self.db_obj, self.attribute_name + '_id', db_id)
