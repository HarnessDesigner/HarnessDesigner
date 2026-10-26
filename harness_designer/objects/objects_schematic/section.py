# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import base_schematic as _base_schematic
from ... import check_types as _check_types


if TYPE_CHECKING:
    from .. import pegboard_section as _pegboard_section
    from ...database.project_db import pjt_pegboard_section as _pjt_pegboard_section


class Section(_base_schematic.BaseSchematic):
    """Concentric section widget -- has no schematic-view presence at all
    (peg-board only), the same inert-placeholder shape as
    ``objects_schematic.table.Table``.
    """

    _parent: "_pegboard_section.PegboardSection" = None
    db_obj: "_pjt_pegboard_section.PJTPegboardSection" = None

    @_check_types.do
    def __init__(self, parent: "_pegboard_section.PegboardSection",
                 db_obj: "_pjt_pegboard_section.PJTPegboardSection"):
        """Initialise the :class:`Section` instance.

        :param parent: Parent object.
        :type parent: :class:`_pegboard_section.PegboardSection`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_pegboard_section.PJTPegboardSection`
        """
        self.db_obj = db_obj
        super().__init__(parent, db_obj, None, None, None, None, None)
        self._is_visible = False
