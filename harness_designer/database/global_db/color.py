# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

import uuid

from .bases import EntryBase, TableBase
from .mixins import NameMixin
from ... import color as _color


class ColorsTable(TableBase):
    """Represent a colors table in :mod:`harness_designer.database.global_db.color`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'colors'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import colors

        return colors.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import colors

        colors.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        colors.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import colors

        colors.table.update_fields(self)

    def __iter__(self) -> _Iterable["Color"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Color']
        """
        for db_id in TableBase.__iter__(self):
            yield Color(self, db_id)

    def __getitem__(self, item) -> "Color":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Color`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Color(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Color(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str, rgb: int) -> "Color":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param rgb: Value for ``rgb``.
        :type rgb: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Color`
        """
        db_id = TableBase.insert(self, name=name, rgb=rgb)
        return Color(self, db_id)


class Color(EntryBase, NameMixin):
    """Represent a color in :mod:`harness_designer.database.global_db.color`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: ColorsTable = None
    _color_id: str = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'colors': [self.db_id],
        }

        return packet

    def _update_color(self, c: _color.Color) -> None:
        """Update the color.

        UNKNOWN details are inferred from the callable name and signature.

        :param c: Value for ``c``.
        :type c: :class:`_color.Color`
        """
        self._table.update(self._db_id, rgb=c.GetRGBA())

    @property
    def ui(self) -> _color.Color:
        """Return the UI.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_color.Color`
        """
        if self._color_id is None:
            self._color_id = str(uuid.uuid4())

        color = _color.Color(*self.rgb, db_id=self._color_id)
        color.bind(self._update_color)
        return color

    @property
    def rgb(self) -> tuple[int, int, int, int]:
        """Return the RGB.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: tuple[int, int, int, int]
        """
        rgba = self._table.select('rgb', id=self._db_id)[0][0]

        r = rgba >> 24
        g = (rgba >> 16) & 0xFF
        b = (rgba >> 8) & 0xFF
        a = rgba & 0xFF
        return r, g, b, a

    @rgb.setter
    def rgb(self, value: tuple[int, int, int, int]):
        """Set the RGB.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: tuple[int, int, int, int]
        """
        r, g, b, a = value

        rgba = r << 24 | b << 16 | b << 8 | a

        self._table.update(self._db_id, rgb=rgba)
        self._populate('rgb')
