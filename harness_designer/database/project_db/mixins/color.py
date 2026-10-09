# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Union as _Union

from PySide6 import QtGui

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType
from .... import check_types as _check_types


if TYPE_CHECKING:
    from ...global_db import color as _color
    from ....ui.prop_ctrls import events as _prop_events
    from PySide6 import QtWidgets


class ColorMixin(BaseMixin):
    """Represent a color mixin in :mod:`harness_designer.database.global_db.mixins.color`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_color: _Union[DefaultStoredValueType, "_color.Color"] = DefaultStoredValue

    @property
    @_check_types.do
    def color(self) -> "_color.Color":
        """Return the color.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_color.Color`
        """

        if self._stored_color is DefaultStoredValue:
            color_id = self._table.select('color_id', id=self._db_id)
            self._stored_color = self._table.db.global_db.colors_table[color_id[0][0]]

        return self._stored_color

    @property
    @_check_types.do
    def color_id(self) -> bytes:
        """Return the color ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: bytes
        """
        _rows = self._table.select('color_id', id=self._db_id)
        return _rows[0][0] if _rows else None

    @color_id.setter
    @_check_types.do
    def color_id(self, value: bytes) -> None:
        """Set the color ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: bytes
        """
        self._stored_color = DefaultStoredValue

        self._table.update(self._db_id, color_id=value)
        self._populate('color_id')


class ColorControl(_prop_ctrls.ColorProperty):
    """Represent a color control in :mod:`harness_designer.database.global_db.mixins.color`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def __init__(self, parent: "QtWidgets.QWidget") -> None:
        """Initialise the :class:`ColorControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.choices: list[list[str, int]] = None
        self.db_obj: ColorMixin | None = None
        super().__init__(parent, 'Color')

        self.propertyChanged.connect(self._on_color)

    @_check_types.do
    def set_obj(self, db_obj: ColorMixin | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`ColorMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.SetItems(self.choices)
            self.SetValue(['', QtGui.QColor(0, 0, 0)])
            self.setEnabled(False)
        else:
            color = db_obj.color

            db_obj.table.execute('SELECT name, rgb from colors;')
            rows = db_obj.table.fetchall()
            self.choices = [list(row) for row in rows]

            self.SetItems(self.choices)
            self.SetValue([color.name, color.ui])
            self.setEnabled(True)

    @_check_types.do
    def _on_color(self, evt: "_prop_events.PropertyEvent") -> None:
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
                self.db_obj.color_id = db_id
                self.db_obj.color.rgb = rgba
        else:
            db_obj = self.db_obj.table.db.colors_table.insert(name, rgba)
            db_id = db_obj.db_id

            self.choices.append([name, color])
            self.SetItems(self.choices)
            self.SetValue([name, color])

        self.db_obj.color_id = db_id
