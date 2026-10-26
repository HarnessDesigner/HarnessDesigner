# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from . import ObjectBase as _ObjectBase
from .objects_3d import section as _section_3d
from .objects_schematic import section as _section_schematic
from .objects_pegboard import section as _section_pegboard
from .objects_pegboard import table_placement as _table_placement
from ..geometry import point as _point
from .. import check_types as _check_types


if TYPE_CHECKING:
    from ..database.project_db import pjt_concentric as _pjt_concentric
    from ..database.project_db import pjt_pegboard_section as _pjt_pegboard_section
    from ..ui import mainframe as _mainframe


class PegboardSection(_ObjectBase):
    """Facade for a concentric section widget -- owns the per-view wrapper
    instances (``objpegboard`` is the only one with any real presence;
    ``obj3d`` and ``objschematic`` are permanently inert), the same shape as
    ``pegboard_table.PegboardTable`` and every other facade in this package.

    One per ``pjt_pegboard_sections`` row, i.e. one per concentric: a bundle
    and a transition branch that share a concentric share this widget.
    """
    objschematic: _section_schematic.Section = None
    obj3d: _section_3d.Section = None
    objpegboard: _section_pegboard.Section = None
    db_obj: "_pjt_pegboard_section.PJTPegboardSection" = None

    @_check_types.do
    def __init__(self, mainframe: "_mainframe.MainFrame",
                 db_obj: "_pjt_pegboard_section.PJTPegboardSection"):
        """Initialise the :class:`PegboardSection` instance.

        :param mainframe: Main application frame.
        :type mainframe: :class:`_mainframe.MainFrame`
        :param db_obj: Database-backed object.
        :type db_obj: :class:`_pjt_pegboard_section.PJTPegboardSection`
        """
        db_obj.set_object(self)
        db_obj.add_object(self)

        super().__init__(mainframe, db_obj)

        self.obj3d = _section_3d.Section(self, db_obj)
        self.objpegboard = _section_pegboard.Section(self, db_obj)
        self.objschematic = _section_schematic.Section(self, db_obj)

        self.mainframe.add_object(self)

    @classmethod
    @_check_types.do
    def show(cls, mainframe: "_mainframe.MainFrame", concentric: "_pjt_concentric.PJTConcentric",
             anchor: _point.Point, obstacles: list) -> "PegboardSection":
        """Show *concentric*'s section widget: create its ``pjt_pegboard_
        sections`` row at the nearest free spot to *anchor* if it has none, or
        un-hide the row (the user closed it) where it already is, and build the
        live facade if this session has not yet. Safe to call when it is
        already showing.

        :param mainframe: Main application frame.
        :param concentric: The concentric whose widget to show.
        :param anchor: Where to search outward from (world X / Z), usually the
            bundle's or the transition's own peg-board position.
        :param obstacles: ``(min_x, min_z, max_x, max_z)`` footprints to keep
            clear of (``table_placement.obstacle_rects_from_objects``).
        :returns: The live facade.
        :rtype: :class:`PegboardSection`
        """
        from ..database.project_db import pjt_pegboard_section as _pjt_pegboard_section  # NOQA -- avoid a cycle at import time

        row = concentric.pegboard_section

        if row is None:
            width = _pjt_pegboard_section.DEFAULT_SECTION_WIDTH
            height = _pjt_pegboard_section.DEFAULT_SECTION_HEIGHT

            # the search works with a rectangle's CENTRE, but the widget is drawn from its LEFT edge in X (and centred in
            # Z), so the stored position is the centre moved half a width to the left
            centre = _table_placement.find_free_position(anchor, width, height, obstacles)
            position = _point.Point(centre.x - (width / 2.0), 0.0, centre.z)

            row = concentric.table.db.pjt_pegboard_sections_table.insert(
                concentric.db_id, position, width, height)
        else:
            row.is_visible_pegboard = True

        section = row.get_object()
        if section is None:
            section = cls(mainframe, row)

        return section

    @_check_types.do
    def delete(self) -> None:
        """Delete this widget and its row (the position point goes with it).
        The owning concentric's own ``delete()`` is responsible for calling
        this, not the other way around, so this only tears down this object's
        own state and its DB row.
        """
        super().delete()
        self.db_obj.delete()
