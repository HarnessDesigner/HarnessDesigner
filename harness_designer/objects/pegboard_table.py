# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_3d import table as _table_3d
from .objects_schematic import table as _table_schematic
from .objects_pegboard import table as _table_pegboard
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.project_db import pjt_pegboard_table as _pjt_pegboard_table
    from ..ui import mainframe as _mainframe


class PegboardTable(_ObjectBase):
    """Facade for a floating wire table -- owns the per-view wrapper
    instances (``objpegboard`` is the only one with any real presence
    today; ``obj3d`` is a placeholder pending the real 3D billboard table,
    BUNDLE_DESIGN.md section 2.7; ``objschematic`` is permanently inert,
    this object type is never shown in the schematic view), same shape as
    every other facade in this package (see ``wire_marker.py``).
    """
    objschematic: _table_schematic.Table = None
    obj3d: _table_3d.Table = None
    objpegboard: _table_pegboard.Table = None
    db_obj: "_pjt_pegboard_table.PJTPegboardTable" = None

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame",
                 db_obj: "_pjt_pegboard_table.PJTPegboardTable") -> None:
        """Initialise the :class:`PegboardTable` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_pegboard_table.PJTPegboardTable`
        """
        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj3d = _table_3d.Table(self, db_obj)
        self.objpegboard = _table_pegboard.Table(self, db_obj)
        self.objschematic = _table_schematic.Table(self, db_obj)

        self.mainframe.add_object(self)

    @_check_types.do
    def delete(self) -> None:
        """Delete this table -- its owning anchor's own ``delete()`` is
        responsible for calling this (mirroring the existing cover_id/
        boot_id accessory-cascade pattern), not the other way around, so
        this only tears down this object's own state and its DB row.
        """
        super().delete()
        self.db_obj.delete()
