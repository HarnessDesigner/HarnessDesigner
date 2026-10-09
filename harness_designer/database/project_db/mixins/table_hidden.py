# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin
from .... import check_types as _check_types


class TableHiddenMixin(BaseMixin):
    """Peg-board data-table overlay shown/hidden flag -- whether this row's
    floating Excel-like data-table overlay
    (``gl.canvas_pegboard.tables_overlay.PegboardTableWidget``) is
    currently shown on the peg board.
    """

    @property
    @_check_types.do
    def is_table_hidden(self) -> bool:
        """Return whether the data-table overlay is hidden.

        :returns: Property value.
        :rtype: bool
        """
        _rows = self._table.select('table_hidden', id=self._db_id)
        return bool(_rows[0][0]) if _rows else None

    @is_table_hidden.setter
    @_check_types.do
    def is_table_hidden(self, value: bool) -> None:
        """Set whether the data-table overlay is hidden.

        :param value: Value to store or process.
        :type value: bool
        """
        self._table.update(self._db_id, table_hidden=int(value))
        self._populate('is_table_hidden')
