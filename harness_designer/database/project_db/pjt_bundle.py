# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>
import uuid

from typing import TYPE_CHECKING, Iterable as _Iterable, Union

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from ..global_db import bundle_cover as _bundle_cover
from ...geometry import line as _line
from .pjt_bases import PJTEntryBase, PJTTableBase, DefaultStoredValue, DefaultStoredValueType
from .mixins import (
    PartMixin,
    StartStopPosition3DMixin, StartStopPosition3DControl,
    Visible3DMixin, Visible3DControl,
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

    from ...objects import bundle as _bundle_obj


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
    def start_control(cls, mainframe):
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
    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import bundle_covers

        bundle_covers.pjt_table.add_to_db(self)

    @_check_types.do
    def _update_table_in_db(self):
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
            yield PJTBundle(self, db_id, self.project_id)

    @_check_types.do
    def __getitem__(self, item) -> "PJTBundle":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundle`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, (int, bytes, uuid.UUID)):
            if item in self:
                return PJTBundle(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    @_check_types.do
    def insert(self, part_id: int, name: str) -> "PJTBundle":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param part_id: Identifier for the part.
        :type part_id: int

        :param name: Name for the project part.
        :type part_id: str

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTBundle`
        """
        db_id = PJTTableBase.insert(self, part_id=part_id, name=name)

        return PJTBundle(self, db_id, self.project_id)


class PJTBundle(PJTEntryBase, PartMixin, StartStopPosition3DMixin,
                Visible3DMixin, NameMixin, NotesMixin, SmoothMixin,
                TablePositionPegMixin, TableHiddenMixin):
    """Represent a PJT bundle in :mod:`harness_designer.database.project_db.pjt_bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTBundlesTable = None

    _stored_diameter: float | None | DefaultStoredValueType = DefaultStoredValue

    @property
    @_check_types.do
    def diameter(self) -> float:
        if self._stored_diameter is DefaultStoredValue:
            self._stored_diameter = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)[0][0]
            
        return self._stored_diameter

    @diameter.setter
    @_check_types.do
    def diameter(self, value: float):
        # TODO: figure out the code that is needed here.
        concentric_id = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)[0][0]

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
    def __release_obj_ref(self, _):
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    @_check_types.do
    def set_object(self, obj: "_bundle_obj.Bundle"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_bundle_obj.Bundle`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @_check_types.do
    def delete(self) -> None:
        """Delete this bundle row, every interior waypoint row it owns,
        and any BundleLayout marking one of those waypoints.

        Mirrors PJTWire.delete -- bundle_id on pjt_points3d has no
        DB-enforced FK (see create_database/points3d.py), so there is no
        cascade delete to rely on; waypoint rows -- and any BundleLayout
        referencing one -- are cleaned up here explicitly instead. Start/
        stop themselves are never touched -- they're owned by whatever
        transition/other bundle the endpoint is attached to, not by this
        bundle.
        """
        layouts_table = self._table.db.pjt_bundle_layouts_table

        for point in self.waypoints3d:
            for row in layouts_table.select('id', position3d_id=point.db_id):
                layout_db = layouts_table[row[0]]
                layout_obj = layout_db.get_object()
                if layout_obj is not None:
                    layout_obj.delete()
                else:
                    layout_db.delete()

            point.delete()

        super().delete()

    @property
    @_check_types.do
    def waypoints3d(self) -> list["_pjt_point3d.PJTPoint3D"]:
        """Every interior 3D waypoint on this bundle, in chain order
        (start and stop themselves are not included -- see
        start_position3d/stop_position3d)."""
        return self._table.db.pjt_points3d_table.for_bundle(self.db_id)

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
        """Return the wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_wire.PJTWire']
        """
        res = []
        for layer in self.concentric.layers:
            res.extend(layer.wires)

        return res
    
    _stored_concentric: "_pjt_concentric.PJTConcentric | None | DefaultStoredValueType" = DefaultStoredValue
    
    @property
    @_check_types.do
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        """Return the concentric.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_concentric.PJTConcentric`
        """
        if self._stored_concentric is DefaultStoredValue:
            concentric_id = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)[0][0]
            if concentric_id is None:
                self._stored_concentric = None
            else:
                self._stored_concentric = self.table.db.pjt_concentrics_table[concentric_id]
        return self._stored_concentric
        
    @property
    @_check_types.do
    def start_layout(self) -> Union["_pjt_bundle_layout.PJTBundleLayout", None]:
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
    def stop_layout(self) -> Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        """Return the stop layout.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: Union['_pjt_bundle_layout.PJTBundleLayout', None]
        """
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.stop_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    _stored_part: "_bundle_cover.BundleCover | DefaultStoredValueType | None" = DefaultStoredValue
    
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


class PJTBundleControl(QTabWidget, LazyTabMixin):
    """Represent a PJT bundle control in :mod:`harness_designer.database.project_db.pjt_bundle`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @_check_types.do
    def set_obj(self, db_obj: PJTBundle):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTBundle`
        """
        self._lazy_set_obj(db_obj)

    @_check_types.do
    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.name_ctrl.set_obj(self.db_obj)
            self.notes_ctrl.set_obj(self.db_obj)
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.start_stop_ctrl.set_obj(self.db_obj)
        elif page is self._part_page:
            self.part_ctrl.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    @_check_types.do
    def __init__(self, parent):
        """Initialise the :class:`PJTBundleControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTBundle = None
        super().__init__(parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
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

        position_page.addWidget(self.start_stop_ctrl)

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
