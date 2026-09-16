# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

"""Excel-like data-table overlay geometry and scroll state.

One row per anchor that has a floating peg-board wire table. Position comes
from :class:`~..mixins.position_pegboard.PositionPegboardMixin` -- via
``point_pegboard_id``, this row's own ``position_pegboard``/
``position_pegboard_id`` -- but that column is deliberately populated with
the SAME ``pjt_points_pegboard`` row as the owning anchor's own
``table_point_peg_id`` (see ``mixins.table_position_peg.
TablePositionPegMixin``, already mixed into every anchor type that can own
one of these overlays: ``PJTHousing``/``PJTBundle``/``PJTTransition``/
``PJTTransitionBranch``), not a fresh point of this row's own. Sharing that
one point is what lets :attr:`PJTPegboardTable.anchor` and
:meth:`PJTPegboardTablesTable.get_from_point_pegboard_id` find one row from
the other with a plain equality lookup, in either direction, without a
forward FK on either side.
"""

import ast
import weakref
from typing import Iterable as _Iterable, Union, TYPE_CHECKING

from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import PositionPegboardMixin, VisiblePegboardMixin
from ...geometry import point as _point
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_housing as _pjt_housing
    from . import pjt_bundle as _pjt_bundle
    from . import pjt_transition as _pjt_transition
    from . import pjt_transition_branch as _pjt_transition_branch
    from ...objects import pegboard_table as _pegboard_table_obj

    _Anchor = Union["_pjt_housing.PJTHousing", "_pjt_bundle.PJTBundle",
                    "_pjt_transition.PJTTransition",
                    "_pjt_transition_branch.PJTTransitionBranch"]


# On the peg board, X/Z are the screen's own two axes (top-down camera) --
# Y is depth, controlling OpenGL's render/occlusion order, not "unused
# height" the way it might read at a glance. A floating table should
# always render on top of every ordinary anchor/wire/bundle underneath
# it, so its own point is created at a fixed, deliberately elevated Y
# rather than 0.0 -- see PJTPegboardTablesTable.insert().
TABLE_DEPTH_Y = 50.0

# Default size, in world-space mm (world units are millimeters everywhere
# else in this codebase too, e.g. wires.od_mm/conductor_dia_mm) -- 100mm
# wide is roughly 2-3x a typical housing's own 30-50mm width, a reasonable
# ratio (Kevin, 2026-09-15) rather than dwarfing nearby components. A
# table row is created at this size both by each anchor table's own
# insert() (see e.g. PJTHousingsTable.insert, which has no live view/AABB
# data available to run a real obstacle-avoiding placement search, so it
# places the row at a naive default right at the anchor's own position)
# and by BasePegboard.show_table's own fallback path for a legacy row from
# before that wiring existed. See ui.pegboard_table.mdi_host.PIXELS_PER_MM
# for the separate (purely cosmetic -- doesn't change this WORLD size) knob
# controlling how many hidden-widget logical pixels represent each mm. A
# user can always resize the table afterward by dragging its own MDI
# sub-window edges.
DEFAULT_TABLE_WIDTH = 100.0
DEFAULT_TABLE_HEIGHT = 50.0


class PJTPegboardTablesTable(PJTTableBase):
    """Table of peg-board data-table overlays, one per anchor."""

    __table_name__ = 'pjt_pegboard_tables'

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Return whether the table is missing any schema fields.

        :returns: ``True`` when the table is missing a defined field.
        :rtype: bool
        """
        from ..create_database import pegboard_tables

        return pegboard_tables.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Create the ``pjt_pegboard_tables`` table in the database."""
        from ..create_database import pegboard_tables

        pegboard_tables.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Add any missing fields to the ``pjt_pegboard_tables`` table."""
        from ..create_database import pegboard_tables

        pegboard_tables.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTPegboardTable"]:
        """Iterate over every data-table overlay row for the open project.

        :returns: An iterator of :class:`PJTPegboardTable` rows.
        :rtype: _Iterable['PJTPegboardTable']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTPegboardTable(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "PJTPegboardTable":
        """Return the data-table overlay row for the given database id.

        :param item: Row id to look up.
        :type item: int
        :returns: The matching row.
        :rtype: :class:`PJTPegboardTable`
        :raises KeyError: Raised when ``item`` is not an ``int``.
        :raises IndexError: Raised when no row with that id exists.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTPegboardTable or item in self:
                return PJTPegboardTable(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, point_id: bytes, position: _point.Point,
              width: float, height: float) -> "PJTPegboardTable":
        """Create a new data-table overlay, anchored to *point_id* --
        the owning anchor's own shared table-position point (its
        ``table_point_peg_id``, see :class:`~.mixins.table_position_peg.
        TablePositionPegMixin`), not a fresh point of this row's own.
        Reusing that exact point (rather than creating a new one) is
        what lets :attr:`PJTPegboardTable.anchor` and
        :meth:`get_from_point_pegboard_id` find one row from the other.

        ``h_scroll``, ``v_scroll`` and ``is_collapsed`` are left at
        their schema defaults (no scroll offset, not collapsed).

        :param point_id: The owning anchor's own
            ``table_point_peg_id`` row -- typically
            ``anchor.table_position_peg_id`` (see
            ``TablePositionPegMixin``, which lazily creates it at
            ``(0.0, 0.0, 0.0)`` the first time it's needed).
        :type point_id: bytes
        :param position: World-space X/Z CENTER of the table -- the
            caller (see ``objects.objects_pegboard.pegboard_table``) is
            responsible for choosing this, typically via a nearest-free-
            spot search against every other object's OBB/AABB so the new
            table doesn't land on top of anything. ``position.y`` is
            IGNORED -- *point_id* is elevated to the fixed
            :data:`TABLE_DEPTH_Y` right here instead, not whatever depth
            the caller's own anchor happens to sit at, so a table always
            renders on top of ordinary scene geometry regardless of
            which anchor it belongs to.
        :type position: :class:`_point.Point`
        :param width: Table width, in world units.
        :type width: float
        :param height: Table height, in world units.
        :type height: float
        :returns: The newly created row.
        :rtype: :class:`PJTPegboardTable`
        """
        point_row = self.db.pjt_points_pegboard_table[point_id]
        with point_row.point:
            point_row.point.x = position.x
            point_row.point.y = TABLE_DEPTH_Y
            point_row.point.z = position.z

        db_id = PJTTableBase.insert(
            self, point_pegboard_id=point_id, size=str((width, height)))

        return PJTPegboardTable(self, db_id)

    @_check_types.do
    def get_from_point_pegboard_id(self, point_id: bytes) -> Union["PJTPegboardTable", None]:
        """Reverse lookup: the overlay row whose own ``point_pegboard_id``
        matches *point_id* -- the SHARED point convention described in
        this module's own docstring. Used by
        ``TablePositionPegMixin.delete_table_overlay`` to find (and
        delete) an anchor's own overlay row, and is the forward-
        direction counterpart of :attr:`PJTPegboardTable.anchor`.

        :param point_id: A ``pjt_points_pegboard`` row id.
        :type point_id: bytes
        :returns: The matching row, or ``None`` if this point has no
            overlay.
        :rtype: :class:`PJTPegboardTable` | None
        """
        rows = self.select('id', point_pegboard_id=point_id)
        if not rows:
            return None

        return PJTPegboardTable(self, rows[0][0])


class PJTPegboardTable(PJTEntryBase, PositionPegboardMixin, VisiblePegboardMixin):
    """A single floating Excel-like data-table overlay on the peg-board
    view.
    """

    _table: PJTPegboardTablesTable = None

    @property
    @_check_types.do
    def table(self) -> PJTPegboardTablesTable:
        """Return the owning table.

        :returns: The table this row belongs to.
        :rtype: :class:`PJTPegboardTablesTable`
        """
        return self._table

    @_check_types.do
    def get_object(self) -> "_pegboard_table_obj.PegboardTable | None":
        """Return the live facade object for this row, if one has been
        constructed -- same weakref-backed pattern as every other
        ``PJTEntryBase`` subclass (e.g. ``PJTBundle.get_object``); this
        row had no override of its own until now, which meant the very
        first ``objects.pegboard_table.PegboardTable(mainframe, db_obj)``
        construction (it calls ``db_obj.set_object(self)`` immediately)
        would have hit ``PJTEntryBase.get_object``/``set_object``'s own
        ``NotImplementedError`` instead.

        :returns: The live facade, or ``None``.
        :rtype: :class:`_pegboard_table_obj.PegboardTable` | None
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _):
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_pegboard_table_obj.PegboardTable | None"):
        """Register the live facade object for this row -- see
        :meth:`get_object`.

        :param obj: Facade instance, or ``None`` to clear it.
        :type obj: :class:`_pegboard_table_obj.PegboardTable` | None
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
            self._process_bind_callbacks(obj)
        else:
            self._obj = obj

    _stored_anchor: "_Anchor | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def anchor(self) -> "_Anchor | None":
        """Return the owning anchor row -- a housing, bundle,
        transition, or transition branch, found by matching this
        table's own :attr:`position_pegboard_id` against each anchor
        type's own ``table_point_peg_id`` column (the same SHARED
        point -- see this module's own docstring, and
        :meth:`PJTPegboardTablesTable.insert`, which is what makes them
        equal in the first place).

        Every anchor type that can own one of these overlays exposes
        the exact same ``name``/``wires``/``position_pegboard`` surface
        (``NameMixin``/``PositionPegboardMixin``, plus each type's own
        ``wires`` -- see ``pjt_housing.PJTHousing.wires`` and its
        siblings), so callers (``objects.objects_pegboard.
        pegboard_table.PegboardTable``) never need to know which one
        this actually is.

        :returns: The owning anchor row, or ``None`` if none of the 4
            anchor tables reference this table's own point (should not
            normally happen for a live table row).
        :rtype: :class:`PJTHousing` | :class:`PJTBundle` | :class:`PJTTransition` | :class:`PJTTransitionBranch` | None
        """
        if self._stored_anchor is DefaultStoredValue:
            point_id = self.position_pegboard_id
            db = self._table.db

            self._stored_anchor = None

            for table in (db.pjt_housings_table, db.pjt_bundles_table,
                         db.pjt_transitions_table, db.pjt_transition_branches_table):
                rows = table.select('id', table_point_peg_id=point_id)
                if rows:
                    self._stored_anchor = table[rows[0][0]]
                    break

        return self._stored_anchor

    _stored_size: tuple[float, float] | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def size(self) -> tuple[float, float]:
        """Return the table's ``(width, height)``, in world units.

        :returns: The table's size.
        :rtype: tuple[float, float]
        """
        if self._stored_size is DefaultStoredValue:
            raw = self._table.select('size', id=self._db_id)[0][0]
            self._stored_size = ast.literal_eval(raw)

        return self._stored_size

    @size.setter
    @_check_types.do
    def size(self, value: tuple[float, float]):
        """Set the table's ``(width, height)``, in world units.

        :param value: New size.
        :type value: tuple[float, float]
        """
        self._stored_size = value
        self._table.update(self._db_id, size=str(value))
        self._populate('size')

    _stored_visible_columns: list[int] | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def visible_columns(self) -> list[int]:
        """Return which columns are shown, and in what order.

        Each int indexes into ``ui.pegboard_table.column_defs.COLUMN_DEFS``
        -- same string-encoded-list-in-a-TextField convention as
        ``wires.accessory_part_nums`` (``'[0, 4, 2]'``, read back via
        ``[1:-1].split(', ')``). An empty stored string means "use the
        default column set" (see the column_defs module).

        :returns: Column indices, in display order.
        :rtype: list[int]
        """
        if self._stored_visible_columns is DefaultStoredValue:
            raw = self._table.select('visible_columns', id=self._db_id)[0][0]
            if raw:
                self._stored_visible_columns = [int(v) for v in raw[1:-1].split(', ')]
            else:
                self._stored_visible_columns = []

        return list(self._stored_visible_columns)

    @visible_columns.setter
    @_check_types.do
    def visible_columns(self, value: list[int]):
        """Set which columns are shown, and in what order.

        :param value: Column indices, in display order.
        :type value: list[int]
        """
        self._stored_visible_columns = value

        db_value = f'[{", ".join(str(v) for v in value)}]'
        self._table.update(self._db_id, visible_columns=db_value)
        self._populate('visible_columns')
