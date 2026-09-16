# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_3d import pegboard_table as _pegboard_table_3d
from .objects_schematic import pegboard_table as _pegboard_table_schematic
from .objects_pegboard import pegboard_table as _pegboard_table_pegboard
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.project_db import pjt_pegboard_table as _pjt_pegboard_table
    from ..ui import mainframe as _mainframe


class PegboardTable(_ObjectBase):
    """Facade for a floating peg-board wire table -- owns the per-view
    wrapper instances (``objpegboard`` is the only one with any real
    presence; ``obj3d``/``objschematic`` are inert placeholders, this
    object type has no rendering presence in either of those views), same
    shape as every other facade in this package (see ``wire_marker.py``).
    """
    objschematic: _pegboard_table_schematic.PegboardTable = None
    obj3d: _pegboard_table_3d.PegboardTable = None
    objpegboard: _pegboard_table_pegboard.PegboardTable = None
    db_obj: "_pjt_pegboard_table.PJTPegboardTable" = None

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame",
                 db_obj: "_pjt_pegboard_table.PJTPegboardTable"):
        """Initialise the :class:`PegboardTable` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_pegboard_table.PJTPegboardTable`
        """
        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj3d = _pegboard_table_3d.PegboardTable(self, db_obj)
        self.objpegboard = _pegboard_table_pegboard.PegboardTable(self, db_obj)
        self.objschematic = _pegboard_table_schematic.PegboardTable(self, db_obj)

        self.mainframe.add_object(self)

    @_check_types.do
    def delete(self):
        """Delete this table -- its owning anchor's own ``delete()`` is
        responsible for calling this (mirroring the existing cover_id/
        boot_id accessory-cascade pattern), not the other way around, so
        this only tears down this object's own state and its DB row.
        """
        super().delete()
        self.db_obj.delete()
