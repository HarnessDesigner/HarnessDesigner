# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from ...geometry import point as _point
from .mixins import (
    Position3DControl,
    Visible3DMixin, Visible3DControl,
    VisiblePegboardMixin,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl
)
from ... import check_types as _check_types


if TYPE_CHECKING:
    from . import pjt_bundle as _pjt_bundle
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_point_pegboard as _pjt_point_pegboard

    from ...objects import bundle_layout as _bundle_layout_obj


class PJTBundleLayoutsTable(PJTTableBase):
    """Represent a PJT bundle layouts table in :mod:`harness_designer.database.project_db.pjt_bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_bundle_layouts'

    _control: "PJTBundleLayoutControl" = None

    @property
    @_check_types.do
    def control(self) -> "PJTBundleLayoutControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayoutControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    @_check_types.do
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTBundleLayoutControl(mainframe)
        cls._control.hide()

    @_check_types.do
    def get_from_position3d_id(self, position3d_id) -> "PJTBundleLayout":
        """Return the from position 3D ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param position3d_id: Identifier for the position 3D.
        :type position3d_id: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayout`
        """
        rows = self.select('id', position3d_id=position3d_id)
        if rows:
            return self[rows[0][0]]

    @_check_types.do
    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import bundle_cover_layouts

        return bundle_cover_layouts.pjt_table.is_ok(self)

    @_check_types.do
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_cover_layouts

        bundle_cover_layouts.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_cover_layouts

        bundle_cover_layouts.pjt_table.update_fields(self)

    @_check_types.do
    def __iter__(self) -> _Iterable["PJTBundleLayout"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTBundleLayout']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundleLayout(self, db_id)

    @_check_types.do
    def __getitem__(self, item) -> "PJTBundleLayout":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayout`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes)):
            if item in PJTBundleLayout or item in self:
                return PJTBundleLayout(self, item)

            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, coord_id: bytes, diameter: float) -> "PJTBundleLayout":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param coord_id: Identifier for the coord.
        :type coord_id: bytes
        :param diameter: Value for ``diameter``.
        :type diameter: float
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayout`
        """
        db_id = PJTTableBase.insert(self, coord_id=coord_id, diameter=diameter)

        return PJTBundleLayout(self, db_id)

    @_check_types.do
    def for_point_pegboard_id(self, point_pegboard_id: bytes) -> "PJTBundleLayout | None":
        """Return the bundle-layout row whose peg-board position is
        *point_pegboard_id*, or ``None`` if no row references it.

        See ``PJTWireLayoutsTable.for_point_pegboard_id`` -- identical
        purpose/shape, mirrored here for bundles.

        :param point_pegboard_id: The waypoint's own row id.
        :type point_pegboard_id: bytes
        :returns: The matching layout row, or ``None``.
        :rtype: PJTBundleLayout | None
        """
        rows = self.select('id', point_pegboard_id=point_pegboard_id)
        if not rows:
            return None

        return self[rows[0][0]]


class PJTBundleLayout(PJTEntryBase, Visible3DMixin, VisiblePegboardMixin, NotesMixin, SmoothMixin):
    """Represent a PJT bundle layout in :mod:`harness_designer.database.project_db.pjt_bundle_layout`.

    Exactly one of :attr:`position3d`/:attr:`position_pegboard` is ever
    non-``NULL`` per row (no schematic variant -- bundles are never shown
    in the schematic view) -- mirrors ``PJTWireLayout``'s own exclusive
    position handling exactly, see that class's docstring for the full
    rationale. Deliberately does NOT use ``Position3DMixin``/
    ``PositionPegboardMixin`` -- both hand-written below instead, with
    each setter clearing the other column to enforce the exclusivity.
    """
    _table: PJTBundleLayoutsTable = None

    _stored_position3d: "_pjt_point3d.PJTPoint3D | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def position3d(self) -> _point.Point | None:
        """Return this waypoint's 3D position, or ``None`` if this
        layout marks a waypoint placed in the peg-board view instead.
        Never auto-creates -- see the class docstring.
        """
        if self._stored_position3d is DefaultStoredValue:
            point_id = self.position3d_id

            if point_id is None:
                self._stored_position3d = None
            else:
                self._stored_position3d = self._table.db.pjt_points3d_table[point_id]

        if self._stored_position3d is not None:
            if self._obj is not None:
                self._stored_position3d.add_object(self._obj())

            point = self._stored_position3d.point
        else:
            point = None

        return point

    _stored_position3d_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def position3d_id(self) -> bytes | None:
        """Return this waypoint's ``pjt_points3d`` row id, or ``None``.
        Never auto-creates -- see the class docstring.
        """
        if self._stored_position3d_id is DefaultStoredValue:
            self._stored_position3d_id = self._table.select('point3d_id', id=self._db_id)[0][0]

        return self._stored_position3d_id

    @position3d_id.setter
    @_check_types.do
    def position3d_id(self, value: bytes | None):
        """Set this waypoint's 3D point row id -- clears
        ``position_pegboard_id`` to ``NULL`` so exactly one view stays
        populated.
        """
        self._stored_position3d_id = value
        self._stored_position3d = DefaultStoredValue
        self._stored_position_pegboard_id = None
        self._stored_position_pegboard = None

        self._table.update(self._db_id, point3d_id=value, point_pegboard_id=None)
        self._populate('position3d_id')
        self._populate('position_pegboard_id')

    _stored_position_pegboard: "_pjt_point_pegboard.PJTPointPegboard | None | DefaultStoredValueType" = DefaultStoredValue

    @property
    @_check_types.do
    def position_pegboard(self) -> _point.Point | None:
        """Return this waypoint's peg-board position, or ``None`` if
        this layout marks a waypoint placed in the 3D view instead.
        Never auto-creates -- see the class docstring.
        """
        if self._stored_position_pegboard is DefaultStoredValue:
            point_id = self.position_pegboard_id

            if point_id is None:
                self._stored_position_pegboard = None
            else:
                self._stored_position_pegboard = self._table.db.pjt_points_pegboard_table[point_id]

        if self._stored_position_pegboard is not None:
            if self._obj is not None:
                self._stored_position_pegboard.add_object(self._obj())

            point = self._stored_position_pegboard.point
        else:
            point = None

        return point

    _stored_position_pegboard_id: bytes | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def position_pegboard_id(self) -> bytes | None:
        """Return this waypoint's ``pjt_points_pegboard`` row id, or
        ``None``. Never auto-creates -- see the class docstring.
        """
        if self._stored_position_pegboard_id is DefaultStoredValue:
            self._stored_position_pegboard_id = self._table.select('point_pegboard_id', id=self._db_id)[0][0]

        return self._stored_position_pegboard_id

    @position_pegboard_id.setter
    @_check_types.do
    def position_pegboard_id(self, value: bytes | None):
        """Set this waypoint's peg-board point row id -- clears
        ``position3d_id`` to ``NULL`` so exactly one view stays
        populated.
        """
        self._stored_position_pegboard_id = value
        self._stored_position_pegboard = DefaultStoredValue
        self._stored_position3d_id = None
        self._stored_position3d = None

        self._table.update(self._db_id, point_pegboard_id=value, point3d_id=None)
        self._populate('position_pegboard_id')
        self._populate('position3d_id')

    @_check_types.do
    def get_object(self) -> "_bundle_layout_obj.BundleLayout":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_bundle_layout_obj.BundleLayout`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    @_check_types.do
    def __release_obj_ref(self, _):
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_bundle_layout_obj.BundleLayout"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle_layout_obj.BundleLayout`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    @_check_types.do
    def attached_bundles(self) -> list["_pjt_bundle.PJTBundle"]:
        """Every bundle whose true start/stop lands on this layout's point.

        Falls back to the ``bundle_id`` tag on the point itself when no
        start/stop match is found -- the layout sits on an interior
        waypoint rather than a bundle's true endpoint, mirroring
        ``PJTWireLayout.attached_wires``.

        :returns: Bundles attached at this layout's position.
        :rtype: list['_pjt_bundle.PJTBundle']
        """
        point3d_id = self.position3d_id
        if point3d_id is not None:
            start_col, stop_col, points_table = (
                'start_point3d_id', 'stop_point3d_id', self._table.db.pjt_points3d_table)
            point_id = point3d_id
        else:
            point_pegboard_id = self.position_pegboard_id
            if point_pegboard_id is None:
                return []

            start_col, stop_col, points_table = (
                'start_point_pegboard_id', 'stop_point_pegboard_id',
                self._table.db.pjt_points_pegboard_table)
            point_id = point_pegboard_id

        db_ids = self._table.db.pjt_bundles_table.select(
            "id", OR=True, **{start_col: point_id, stop_col: point_id})

        res = [self._table.db.pjt_bundles_table[db_id[0]] for db_id in db_ids]
        if res:
            return res

        point = points_table[point_id]
        bundle_id = point.bundle_id
        if bundle_id is not None:
            return [self._table.db.pjt_bundles_table[bundle_id]]

        return []

    @property
    @_check_types.do
    def table(self) -> PJTBundleLayoutsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTBundleLayoutsTable`
        """
        return self._table
    
    _stored_diameter: float | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def diameter(self) -> float:
        """Return the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_diameter is DefaultStoredValue:
            
            self._stored_diameter = self._table.select('diameter', id=self._db_id)[0][0]
            
        return self._stored_diameter

    @diameter.setter
    @_check_types.do
    def diameter(self, value: float):
        """Set the diameter.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_diameter = value
        
        self._table.update(self._db_id, diameter=value)
        self._populate('diameter')


class PJTBundleLayoutControl(QTabWidget, LazyTabMixin):
    """Represent a PJT bundle layout control in :mod:`harness_designer.database.project_db.pjt_bundle_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTBundleLayout | None):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTBundleLayout`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.notes_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
            if self.db_obj is None:
                self.diameter_ctrl.SetValue('')
            else:
                self.diameter_ctrl.SetValue(str(self.db_obj.diameter))
        elif page is self._visible_page:
            self.visible_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position_ctrl.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`PJTBundleLayoutControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTBundleLayout | None = None
        super().__init__(parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')
        self.notes_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)

        self.diameter_ctrl = _prop_ctrls.StringProperty(general_page, 'Diameter', read_only=True)

        general_page.addWidget(self.notes_ctrl)
        general_page.addWidget(self.smooth_ctrl)
        general_page.addWidget(self.diameter_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position_ctrl = Position3DControl(position_page)

        position_page.addWidget(self.position_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible_ctrl)

        for page in (
            general_page,
            visible_page,
            position_page
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
