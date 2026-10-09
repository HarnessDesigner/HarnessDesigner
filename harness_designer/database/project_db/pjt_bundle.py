# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable, Union as _Union

import weakref
from PySide6 import QtWidgets

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import bundle_cover as _bundle_cover
from ...geometry import line as _line
from ...geometry import point as _point
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import (
    PartMixin,
    StartStopPosition3DMixin, StartStopPosition3DControl,
    StartStopPositionPegboardMixin, StartStopPositionPegboardControl,
    Visible3DMixin, Visible3DControl,
    VisiblePegboardMixin,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl,
    TablePositionPegMixin,
    TableHiddenMixin
)
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_concentric as _pjt_concentric
    from . import pjt_bundle_layout as _pjt_bundle_layout
    from . import pjt_wire as _pjt_wire
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_point_pegboard as _pjt_point_pegboard

    from ...objects import bundle as _bundle_obj
    from ... import ui as _ui


class PJTBundlesTable(PJTTableBase):
    """Represent a PJT bundles table in :mod:`harness_designer.database.project_db.pjt_bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_bundles'

    _control: "PJTBundleControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTBundleControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundleControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    @_check_types.do
    def start_control(cls, mainframe: "_ui.MainFrame") -> None:
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTBundleControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import bundle_covers

        return bundle_covers.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self) -> None:
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_covers

        bundle_covers.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self) -> None:
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_covers

        bundle_covers.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTBundle"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTBundle']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundle(self, db_id)

    @_check_types.do
    def __getitem__(self, item: int | bytes | str) -> "PJTBundle":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundle`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTBundle or item in self:
                return PJTBundle(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(
        self, part_id: bytes, name: str, start_point3d_id: bytes, stop_point3d_id: bytes
    ) -> "PJTBundle":
        """Execute the insert operation.

        :param part_id: Identifier for the part.
        :type part_id: bytes

        :param name: Name for the project part.
        :type name: str

        :param start_point3d_id: The bundle's own start point (``pjt_points3d``
            row id) -- ``pjt_bundles.start_point3d_id`` is ``NOT NULL`` with no
            default, so this must be supplied at insert time (a fresh
            placeholder point works fine; callers reassign it later via
            ``start_position3d_id`` as placement/merge progresses).
        :type start_point3d_id: bytes

        :param stop_point3d_id: Same as *start_point3d_id*, for the bundle's
            own stop point.
        :type stop_point3d_id: bytes

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundle`
        """
        db_id = PJTTableBase.insert(
            self, part_id=part_id, name=name,
            start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
            start_point_pegboard_id=None, stop_point_pegboard_id=None,
            notes='', is_visible3d=1, is_visible_pegboard=1, smooth=None,
            table_point_peg_id=None, table_hidden=0)

        db_obj = PJTBundle(self, db_id)

        # See PJTHousingsTable.insert's own comment -- same wiring, every
        # anchor type that can own a peg-board data-table overlay gets
        # its own row created right here. A bundle has no single
        # position_pegboard of its own (StartStopPositionPegboardMixin,
        # not PositionPegboardMixin -- it runs between two points, not
        # one), so the placeholder position is the midpoint of its own
        # just-lazily-created start/stop peg-board points instead.
        from . import pjt_pegboard_table as _pjt_pegboard_table

        start = db_obj.start_position_pegboard
        stop = db_obj.stop_position_pegboard
        mid_x = (start.x + stop.x) / 2.0
        mid_z = (start.z + stop.z) / 2.0

        table_point_id = db_obj.table_position_peg_id
        self.db.pjt_pegboard_tables_table.insert(
            table_point_id, _point.Point(mid_x, 0.0, mid_z),
            _pjt_pegboard_table.DEFAULT_TABLE_WIDTH, _pjt_pegboard_table.DEFAULT_TABLE_HEIGHT)

        return db_obj


class PJTBundle(PJTEntryBase, PartMixin, StartStopPosition3DMixin,
                StartStopPositionPegboardMixin,
                Visible3DMixin, VisiblePegboardMixin, NameMixin, NotesMixin, SmoothMixin,
                TablePositionPegMixin, TableHiddenMixin):
    """Represent a PJT bundle in :mod:`harness_designer.database.project_db.pjt_bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTBundlesTable = None

    @property
    @_check_types.do
    def diameter(self) -> float:
        """This bundle's own effective diameter, computed fresh on every
        access -- never a stored column, and never cached (there is no
        single moment that could invalidate a cache: a wire added or
        removed, a concentric repack, or an attached transition branch's
        own catalog part changing could all move this number, and none
        of them notify this row).

        Was a stub before 2026-10-01 (the getter actually returned a
        ``pjt_concentrics`` row id, mislabeled as a diameter, and the
        setter was an unfinished TODO that wrote nothing at all -- see
        ``BUNDLE_PLACEMENT.md`` section 8/4c and ``objects.bom.
        build_bundle_cut_sheet``'s own workaround, now stale). Delegates
        to ``handlers.bundle_diameter.effective_diameter`` -- see that
        module's own docstring for the real rule (the larger of what
        this bundle's own wires need and any attached transition
        branch's own catalog minimum, growing that branch's own
        ``diameter`` to match when the wires need more room than its
        minimum allows). Read-only: the old setter never did anything
        real, and there is no longer a single stored value here to set --
        change the bundle's own wires or attached branch instead, and
        this follows automatically.
        """
        from ...handlers import bundle_diameter as _bundle_diameter

        return _bundle_diameter.effective_diameter(self)

    @_check_types.do
    def get_object(self) -> "_bundle_obj.Bundle":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_bundle_obj.Bundle`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _: weakref.ref) -> None:
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_bundle_obj.Bundle") -> None:
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle_obj.Bundle`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
            self._process_bind_callbacks(obj)
        else:
            self._obj = obj

    @_check_types.do
    def delete(self) -> None:
        """Delete this bundle row and any BundleLayout marking one of its
        interior waypoints. The waypoint point rows themselves are left
        alone -- deliberately, not an oversight; see PJTWire.delete's own
        docstring for why (a waypoint point isn't necessarily owned
        exclusively by this bundle -- the same shared-anchor-point-reused-
        as-a-waypoint hazard applies here too).

        This bundle's own waypoint list rows (``pjt_bundle_paths``) are
        deleted here too, in every view -- the shared point rows they
        referenced are left alone, same as above. There is no cascade
        delete to rely on for the BundleLayout markers either; those ARE
        still cleaned up here explicitly. Start/stop themselves are never
        touched -- they're owned by whatever transition/other bundle the
        endpoint is attached to, not by this bundle.

        Also cascades to this bundle's own peg-board data-table overlay
        row, if it has one (Phase 4 of the point-safety-check rollout,
        2026-09-02, see TODO.md and ``TablePositionPegMixin.
        delete_table_overlay``'s own docstring).
        """
        layouts_table = self._table.db.pjt_bundle_layouts_table

        for point in self.waypoints3d:
            for row in layouts_table.select('id', point3d_id=point.db_id):
                layout_db = layouts_table[row[0]]
                layout_obj = layout_db.get_object()
                if layout_obj is not None:
                    layout_obj.delete()
                else:
                    layout_db.delete()

        for point in self.waypoints_pegboard:
            for row in layouts_table.select('id', point_pegboard_id=point.db_id):
                layout_db = layouts_table[row[0]]
                layout_obj = layout_db.get_object()
                if layout_obj is not None:
                    layout_obj.delete()
                else:
                    layout_db.delete()

        self._table.db.pjt_bundle_paths_table.delete_for_bundle(self.db_id)

        self.delete_table_overlay()

        super().delete()

    @property
    @_check_types.do
    def waypoints3d(self) -> list["_pjt_point3d.PJTPoint3D"]:
        """Every interior 3D waypoint on this bundle, in chain order
        (start and stop themselves are not included -- see
        start_position3d/stop_position3d)."""
        points_table = self._table.db.pjt_points3d_table
        point_ids = self._table.db.pjt_bundle_paths_table.point_ids(self.db_id, '3d')

        return [points_table[point_id] for point_id in point_ids]

    @property
    @_check_types.do
    def waypoints_pegboard(self) -> list["_pjt_point_pegboard.PJTPointPegboard"]:
        """Every interior peg-board waypoint on this bundle, in chain
        order (start and stop themselves are not included -- see
        start_position_pegboard/stop_position_pegboard). No schematic
        equivalent exists -- bundles are never shown in the schematic
        view."""
        points_table = self._table.db.pjt_points_pegboard_table
        point_ids = self._table.db.pjt_bundle_paths_table.point_ids(self.db_id, 'pegboard')

        return [points_table[point_id] for point_id in point_ids]

    @property
    @_check_types.do
    def position_pegboard(self) -> "_point.Point":
        """A single peg-board position for generic anchor-position readers
        that only know about single-position anchors (currently only
        ``objects_pegboard.table.Table.__init__``, for its
        connector line to this bundle's own floating wire table) -- a
        bundle has no single peg-board position of its own
        (``StartStopPositionPegboardMixin`` runs between two points, not
        one, unlike ``PositionPegboardMixin``).

        The first interior waypoint if this bundle has one, else the stop
        end -- NOT a midpoint of start/stop (a bundle with waypoints can
        bend arbitrarily far from that straight-line midpoint, which would
        leave the connector line pointing at empty space next to the
        bundle rather than at a real point on its own path). Always the
        real, live point row -- never a cached/derived copy -- so it needs
        no rebinding when an endpoint's own point row is swapped for a
        different one (e.g. attaching to a transition branch).
        """
        waypoints = self.waypoints_pegboard
        if waypoints:
            return waypoints[0].point

        return self.stop_position_pegboard

    @property
    @_check_types.do
    def table(self) -> PJTBundlesTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundlesTable`
        """
        return self._table

    @property
    @_check_types.do
    def length_mm(self) -> float:
        """Total physical length: the sum of every sub-segment from
        start, through each interior waypoint in order, to stop -- not
        the straight-line distance between the two endpoints, since a
        bundle can have any number of bends between them (see PJTWire.
        length_mm, the same fix for the same reason)."""
        points = [self.start_position3d, *(p.point for p in self.waypoints3d), self.stop_position3d]

        total = 0.0
        for a, b in zip(points, points[1:]):
            total += _line.Line(a, b).length()

        return total

    @property
    @_check_types.do
    def length_m(self) -> float:
        """Straight-line length between this segment's start and stop points, in meters."""
        return self.length_mm / 1000.0

    @property
    @_check_types.do
    def wires(self) -> list["_pjt_wire.PJTWire"]:
        """Every real wire inside this bundle's own span, de-duplicated.

        Prefers the general ``pjt_wire_paths`` tag (``bundle_id`` -- see
        BUNDLE_DESIGN.md section 2.6, "membership must not depend on
        concentric packing"), falling back to this bundle's own
        concentric layers (unwrapping each row's own ``.wire`` -- a
        layer's own ``wires`` are ``PJTConcentricWire`` join rows, not
        ``PJTWire`` itself; the previous version of this returned those
        join rows directly, contradicting its own declared return type
        and ``objects_3d.bundle.Bundle._delete``'s own
        ``concentric_wire.wire.get_object()`` unwrap of exactly the same
        list) for as long as routing a wire through a bundle without
        concentric-twisting it has no UI entry point of its own yet (see
        BUNDLE_DESIGN.md section 2.6's own "Written, but never run"
        audit). Mirrors ``PJTBundleLayout.attached_bundles``'s/
        ``PJTWireLayout.attached_wires``'s own "general tag, concentric
        fallback" shape.

        :returns: Property value.
        :rtype: list['_pjt_wire.PJTWire']
        """
        wire_ids = self._table.db.pjt_wire_paths_table.wire_ids_for_bundle(self.db_id)
        if wire_ids:
            return [self._table.db.pjt_wires_table[wire_id] for wire_id in wire_ids]

        concentric = self.concentric
        if concentric is None:
            return []

        res = []
        seen = set()
        for layer in concentric.layers:
            for concentric_wire in layer.wires:
                wire = concentric_wire.wire
                if wire.db_id not in seen:
                    seen.add(wire.db_id)
                    res.append(wire)

        return res

    @property
    @_check_types.do
    def concentric(self) -> _Union["_pjt_concentric.PJTConcentric", None]:
        """Return this bundle's own concentric-twisting row, or ``None``.

        A skeleton bundle no longer gets an empty placeholder concentric
        row at placement time (concentric twisting is being redesigned --
        not every harness is concentric-twisted -- see
        ``objects_3d.bundle.Bundle.start_add``'s own docstring), so
        ``None`` is now the common case, not an edge case: every reader
        of this property must handle it.
        """
        rows = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)
        concentric_id = rows[0][0] if rows else None
        if concentric_id is not None:
            return self.table.db.pjt_concentrics_table[concentric_id]
        
    @property
    @_check_types.do
    def start_layout(self) -> _Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        """Return the start layout.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: Union['_pjt_bundle_layout.PJTBundleLayout', None]
        """
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.start_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    @property
    @_check_types.do
    def stop_layout(self) -> _Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        """Return the stop layout.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: Union['_pjt_bundle_layout.PJTBundleLayout', None]
        """
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.stop_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    _stored_part: _bundle_cover.BundleCover | DefaultStoredValueType | None = DefaultStoredValue
    
    @property
    @_check_types.do
    def part(self) -> _bundle_cover.BundleCover:
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_bundle_cover.BundleCover`
        """
        if self._stored_part is DefaultStoredValue:        
            part_id = self.part_id
            if part_id is None:
                self._stored_part = None
            else:
                self._stored_part = self._table.db.global_db.bundle_covers_table[part_id]
            
        return self._stored_part


class PJTBundleControl(QtWidgets.QTabWidget, LazyTabMixin):
    """Represent a PJT bundle control in :mod:`harness_designer.database.project_db.pjt_bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTBundle | None) -> None:
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTBundle`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int) -> None:
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.notes_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.start_stop_ctrl.set_obj(self.db_obj)
            self.start_stop_pegboard_ctrl.set_obj(self.db_obj)
        elif page is self._part_page:
            self.part_ctrl.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    @_check_types.do
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        """Initialise the :class:`PJTBundleControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTBundle | None = None
        super().__init__(parent)
        self.setTabPosition(QtWidgets.QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')

        self.name_ctrl = NameControl(general_page)
        self.notes_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)

        general_page.addWidget(self.name_ctrl)
        general_page.addWidget(self.notes_ctrl)
        general_page.addWidget(self.smooth_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.start_stop_ctrl = StartStopPosition3DControl(position_page)
        self.start_stop_pegboard_ctrl = StartStopPositionPegboardControl(position_page)

        position_page.addWidget(self.start_stop_ctrl)

        position_page.addWidget(self.start_stop_pegboard_ctrl)

        self._part_page = part_page = _prop_ctrls.Category(self, 'Part')
        self.part_ctrl = _bundle_cover.BundleCoverControl(part_page)

        part_page.addWidget(self.part_ctrl)

        for page in (
            general_page,
            visible_page,
            position_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
