# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from ..common_db.lazy_tab_mixin import LazyTabMixin
from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    Position3DMixin, Position3DControl,
    Position2DMixin, Position2DControl,
    Visible3DMixin, Visible2DControl,
    Visible2DMixin, Visible3DControl,
    SmoothMixin, SmoothControl
)


if TYPE_CHECKING:
    from . import pjt_wire as _pjt_wire
    from ...objects import wire_layout as _wire_layout_obj


class PJTWireLayoutsTable(PJTTableBase):
    """Represent a PJT wire layouts table in :mod:`harness_designer.database.project_db.pjt_wire_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_wire_layouts'

    _control: "PJTWireLayoutControl" = None

    @property
    def control(self) -> "PJTWireLayoutControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireLayoutControl`
        :raises RuntimeError: Raised when the operation cannot be completed.
        """
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        """Start the control.

        UNKNOWN details are inferred from the callable name and signature.

        :param mainframe: Main application frame.
        :type mainframe: UNKNOWN
        """
        cls._control = PJTWireLayoutControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import wire_layouts

        return wire_layouts.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_layouts

        wire_layouts.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_layouts

        wire_layouts.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTWireLayout"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTWireLayout']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireLayout(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWireLayout":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWireLayout`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTWireLayout(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, point3d_id: int) -> "PJTWireLayout":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param point3d_id: Identifier for the point.
        :type point3d_id: int
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWireLayout`
        """
        db_id = PJTTableBase.insert(self, point3d_id=point3d_id)
        return PJTWireLayout(self, db_id, self.project_id)


class PJTWireLayout(PJTEntryBase, Position3DMixin, Position2DMixin,
                    Visible3DMixin, Visible2DMixin, SmoothMixin):
    """Represent a PJT wire layout in :mod:`harness_designer.database.project_db.pjt_wire_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _table: PJTWireLayoutsTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        position3d_id = self.position3d_id
        position2d_id = self.position2d_id

        packet = {
            'pjt_wire_layouts': [self.db_id]
        }
        if position3d_id is not None:
            packet['pjt_points3d'] = [position3d_id]

        if position2d_id is not None:
            packet['pjt_points2d'] = [position2d_id]

        return packet

    def get_object(self) -> "_wire_layout_obj.WireLayout":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_wire_layout_obj.WireLayout`
        """
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        """Release the obj ref.

        UNKNOWN details are inferred from the callable name and signature.

        :param _: Value for ``_``.
        :type _: UNKNOWN
        """
        self._obj = None

    def set_object(self, obj: "_wire_layout_obj.WireLayout"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_layout_obj.WireLayout`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def attached_wires(self) -> list["_pjt_wire.PJTWire"]:
        """Return the attached wires.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_pjt_wire.PJTWire']
        """
        res = []
        point_id = self.position3d_id
        db_ids = self._table.db.pjt_wires_table.select(
            "id", OR=True, start_point3d_id=point_id, stop_point3d_id=point_id)
        for db_id in db_ids:
            res.append(self._table.db.pjt_wires_table[db_id[0]])

        return res

    @property
    def table(self) -> PJTWireLayoutsTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireLayoutsTable`
        """
        return self._table


class PJTWireLayoutControl(QTabWidget, LazyTabMixin):
    """Represent a PJT wire layout control in :mod:`harness_designer.database.project_db.pjt_wire_layout`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTWireLayout):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTWireLayout`
        """
        self._lazy_set_obj(db_obj)

    def _load_tab(self, index: int):
        page = self.widget(index)
        if page is self._general_page:
            self.smooth_ctrl.set_obj(self.db_obj)
        elif page is self._position_page:
            self.position2d_ctrl.set_obj(self.db_obj)
            self.position3d_ctrl.set_obj(self.db_obj)
        elif page is self._visible_page:
            self.visible2d_ctrl.set_obj(self.db_obj)
            self.visible3d_ctrl.set_obj(self.db_obj)
        self._tab_loaded[index] = True

    def __init__(self, parent):
        """Initialise the :class:`PJTWireLayoutControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTWireLayout = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        self._general_page = general_page = _prop_ctrls.Category(self, 'General')
        self.smooth_ctrl = SmoothControl(general_page)

        general_page.addWidget(self.smooth_ctrl)

        self._position_page = position_page = _prop_ctrls.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        position_page.addWidget(self.position2d_ctrl)
        position_page.addWidget(self.position3d_ctrl)

        self._visible_page = visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        visible_page.addWidget(self.visible2d_ctrl)
        visible_page.addWidget(self.visible3d_ctrl)

        for page in (
            general_page,
            position_page,
            visible_page,
        ):
            self.addTab(page, page.GetLabel())

        self._init_lazy_tabs()
