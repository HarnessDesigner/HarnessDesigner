# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


class TableHiddenMixin(BaseMixin):
    """Peg-board data-table overlay shown/hidden flag -- whether this row's
    floating Excel-like data-table overlay
    (``gl.canvas_pegboard.tables_overlay.PegboardTableWidget``) is
    currently shown on the peg board.
    """

    _stored_is_table_hidden: bool | DefaultStoredValueType = DefaultStoredValue

    @property
    def is_table_hidden(self) -> bool:
        """Return whether the data-table overlay is hidden.

        :returns: Property value.
        :rtype: bool
        """
        if self._stored_is_table_hidden is DefaultStoredValue:
            self._stored_is_table_hidden = bool(self._table.select('table_hidden', id=self._db_id)[0][0])

        return self._stored_is_table_hidden

    @is_table_hidden.setter
    def is_table_hidden(self, value: bool):
        """Set whether the data-table overlay is hidden.

        :param value: Value to store or process.
        :type value: bool
        """
        self._stored_is_table_hidden = value

        self._table.update(self._db_id, table_hidden=int(value))
        self._populate('is_table_hidden')
