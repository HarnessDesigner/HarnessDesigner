# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Placement and size of a concentric-twist cross-section widget on the
peg board.

One row per concentric (``concentric_id`` is UNIQUE in the schema -- see
``create_database/pegboard_sections.py``): a concentric that is shared by a
connected bundle and transition branch still has exactly one widget. Position
comes from :class:`~.mixins.position_pegboard.PositionPegboardMixin` through
``point_pegboard_id``, which here is this row's OWN ``pjt_points_pegboard``
row (the widget's anchor: the X of its LEFT edge and the Z of its vertical
middle), not a point shared with an anchor the way ``PJTPegboardTable``
shares one.
"""

from typing import Iterable as _Iterable, Union as _Union, TYPE_CHECKING

import ast
import weakref

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import PositionPegboardMixin, VisiblePegboardMixin
from ...geometry import point as _point
from ... import check_types as _check_types
from ...crash_dump import capturable, dump_property


if TYPE_CHECKING:
    from . import pjt_concentric as _pjt_concentric
    from ...objects import pegboard_section as _pegboard_section_obj


# On the peg board X/Z are the screen's own two axes (top-down camera) and Y
# is depth, i.e. render / occlusion order. A section widget sits just BELOW
# the floating wire tables (``pjt_pegboard_table.TABLE_DEPTH_Y`` = 50.0) so a
# table dragged over a section is drawn on top of it, and well above the
# ordinary anchors, wires and bundles beneath.
SECTION_DEPTH_Y = 49.0

# Default size in world mm (world units are millimeters everywhere in this
# codebase). A bundle cross-section is a few to a few tens of mm across, so the
# widget is drawn magnified; the cross-section pane and the information pane
# share this footprint. The user can resize it afterward like the tables.
DEFAULT_SECTION_WIDTH = 120.0
DEFAULT_SECTION_HEIGHT = 60.0


class PJTPegboardSectionsTable(PJTTableBase):
    """Table of concentric cross-section widget placements, one per concentric."""

    __table_name__ = 'pjt_pegboard_sections'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Return whether the table is missing any schema fields.

        :returns: ``True`` when the table is missing a defined field.
        :rtype: bool
        """
        from ..create_database import pegboard_sections

        return pegboard_sections.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Create the ``pjt_pegboard_sections`` table in the database."""
        from ..create_database import pegboard_sections

        pegboard_sections.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Add any missing fields to the ``pjt_pegboard_sections`` table."""
        from ..create_database import pegboard_sections

        pegboard_sections.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTPegboardSection"]:
        """Iterate over every section widget row for the open project.

        :returns: An iterator of :class:`PJTPegboardSection` rows.
        :rtype: _Iterable['PJTPegboardSection']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTPegboardSection(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTPegboardSection":
        """Return the section widget row for the given database id.

        :param item: Row id to look up.
        :type item: int | bytes | str
        :returns: The matching row.
        :rtype: :class:`PJTPegboardSection`
        :raises KeyError: Raised when ``item`` is not an ``int`` or ``bytes``.
        :raises IndexError: Raised when no row with that id exists.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTPegboardSection or item in self:
                return PJTPegboardSection(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, concentric_id: bytes, position: _point.Point,
               width: float, height: float) -> "PJTPegboardSection":
        """Create the section widget row for *concentric_id*.

        There is exactly one widget per concentric (the schema's UNIQUE
        constraint rejects a second), so a caller asks
        :meth:`for_concentric` first and only inserts when it returns
        ``None``. The row owns a brand new ``pjt_points_pegboard`` row for
        its center, created here at the fixed :data:`SECTION_DEPTH_Y`.

        :param concentric_id: The ``pjt_concentrics`` row this widget shows.
        :type concentric_id: bytes
        :param position: World-space anchor of the widget: ``position.x`` is
            its LEFT edge and ``position.z`` its vertical MIDDLE (the quad is
            drawn that way, see ``shapes.rectangle.create_vbo_based``).
            ``position.y`` is IGNORED -- the point is created at
            :data:`SECTION_DEPTH_Y`.
        :type position: :class:`_point.Point`
        :param width: Widget width, in world units.
        :type width: float
        :param height: Widget height, in world units.
        :type height: float
        :returns: The newly created row.
        :rtype: :class:`PJTPegboardSection`
        """
        point_row = self.db.pjt_points_pegboard_table.insert(
            x=position.x, y=SECTION_DEPTH_Y, z=position.z)

        db_id = PJTTableBase.insert(
            self, concentric_id=concentric_id, point_pegboard_id=point_row.db_id,
            size=str((width, height)), is_visible_pegboard=1)

        return PJTPegboardSection(self, db_id)

    @_check_types.do
    def for_concentric(self, concentric_id: bytes) -> _Union["PJTPegboardSection", None]:
        """Return the one widget row of *concentric_id*.

        :param concentric_id: A ``pjt_concentrics`` row id.
        :type concentric_id: bytes
        :returns: The widget row, or ``None`` when this concentric has no
            widget yet.
        :rtype: :class:`PJTPegboardSection` | None
        """
        rows = self.select('id', concentric_id=concentric_id)
        if not rows:
            return None

        return PJTPegboardSection(self, rows[0][0])


@capturable()
class PJTPegboardSection(PJTEntryBase, PositionPegboardMixin, VisiblePegboardMixin):
    """Placement and size of one concentric cross-section widget on the peg
    board view.
    """

    _table: PJTPegboardSectionsTable = None

    @property
    @_check_types.do
    def table(self) -> PJTPegboardSectionsTable:
        """Return the owning table.

        :returns: The table this row belongs to.
        :rtype: :class:`PJTPegboardSectionsTable`
        """
        return self._table

    @_check_types.do
    def get_object(self) -> _Union["_pegboard_section_obj.PegboardSection", None]:
        """Return the live facade for this row, if one has been built --
        the same weakref-backed pattern as every other ``PJTEntryBase``
        subclass (``PJTPegboardTable.get_object``). Stays ``None`` until
        ``objects.pegboard_section.PegboardSection(mainframe, db_obj)`` is
        constructed (it calls :meth:`set_object` straight away).

        :returns: The live facade, or ``None``.
        :rtype: :class:`_pegboard_section_obj.PegboardSection` | None
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _: weakref.ref) -> None:
        self._obj = None

    @_check_types.do
    def set_object(self, obj: _Union["_pegboard_section_obj.PegboardSection", None]) -> None:
        """Register the live facade for this row -- see :meth:`get_object`.

        :param obj: Facade instance, or ``None`` to clear it.
        :type obj: :class:`_pegboard_section_obj.PegboardSection` | None
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
            self._process_bind_callbacks(obj)
        else:
            self._obj = obj

    @property
    @dump_property(severity=2)
    @_check_types.do
    def concentric_id(self) -> bytes:
        """Return the ``pjt_concentrics`` row this widget shows.

        :returns: The concentric's row id.
        :rtype: bytes
        """
        return self._table.select('concentric_id', id=self._db_id)[0][0]

    @property
    @_check_types.do
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        """Return the concentric this widget shows. Its ``bundle`` and
        ``transition_branch`` are what the widget is attached to -- both are
        set when a bundle and a transition branch are connected.

        :returns: The concentric row.
        :rtype: :class:`_pjt_concentric.PJTConcentric`
        """
        return self._table.db.pjt_concentrics_table[self.concentric_id]

    @property
    @dump_property(severity=2)
    @_check_types.do
    def size(self) -> tuple[float, float]:
        """Return the widget's ``(width, height)``, in world units.

        :returns: The widget's size.
        :rtype: tuple[float, float]
        """
        raw = self._table.select('size', id=self._db_id)[0][0]
        return ast.literal_eval(raw)

    @size.setter
    @_check_types.do
    def size(self, value: tuple[float, float]) -> None:
        """Set the widget's ``(width, height)``, in world units.

        :param value: New size.
        :type value: tuple[float, float]
        """
        self._table.update(self._db_id, size=str(value))
        self._populate('size')

    @_check_types.do
    def delete(self) -> None:
        """Delete this row, then the center point it owns (the point's own
        :meth:`~.pjt_point_pegboard.PJTPointPegboard.delete` still checks
        that nothing else references it).
        """
        point_id = self.position_pegboard_id
        points = self._table.db.pjt_points_pegboard_table

        super().delete()

        points[point_id].delete()
