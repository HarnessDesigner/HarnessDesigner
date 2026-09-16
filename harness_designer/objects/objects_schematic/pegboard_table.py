# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_schematic as _base_schematic
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import pegboard_table as _pegboard_table
    from ...database.project_db import pjt_pegboard_table as _pjt_pegboard_table


class PegboardTable(_base_schematic.BaseSchematic):
    """Peg-board floating wire table -- has no schematic-view presence
    at all (peg-board-only overlay), same inert-placeholder shape as
    ``objects_schematic.note.Note``'s own no-``position2d_id`` branch.
    """

    _parent: "_pegboard_table.PegboardTable" = None
    db_obj: "_pjt_pegboard_table.PJTPegboardTable" = None

    @_check_types.do
    def __init__(self, parent: "_pegboard_table.PegboardTable",
                 db_obj: "_pjt_pegboard_table.PJTPegboardTable"):
        """Initialise the :class:`PegboardTable` instance.

        :param parent: Parent object.
        :type parent: :class:`_pegboard_table.PegboardTable`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_pegboard_table.PJTPegboardTable`
        """
        self.db_obj = db_obj
        super().__init__(parent, db_obj, None, None, None, None, None)
        self._is_visible = False
