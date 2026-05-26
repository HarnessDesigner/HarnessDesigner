# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from PySide6.QtWidgets import QTabWidget

from ...ui import prop_ctrls as _prop_ctrls
from .pjt_bases import PJTEntryBase, PJTTableBase
from ..global_db import wire_marker as _wire_marker
from .mixins import (
    Position2DMixin, Position2DControl,
    Position3DMixin, Position3DControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl,
    SmoothMixin, SmoothControl
)


if TYPE_CHECKING:
    from . import pjt_wire as _pjt_wire
    from ...objects import wire_marker as _wire_marker_obj


class PJTWireMarkersTable(PJTTableBase):
    """Represent a PJT wire markers table in :mod:`harness_designer.database.project_db.pjt_wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'pjt_wire_markers'

    _control: "PJTWireMarkerControl" = None

    @property
    def control(self) -> "PJTWireMarkerControl":
        """Return the control.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireMarkerControl`
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
        cls._control = PJTWireMarkerControl(mainframe)
        cls._control.hide()

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import wire_markers

        return wire_markers.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_markers

        wire_markers.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import wire_markers

        wire_markers.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTWireMarker"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['PJTWireMarker']
        """
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireMarker(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWireMarker":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWireMarker`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return PJTWireMarker(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, point2d_id: int, point3d_id: int,
               wire_id: int, part_id: int, label: str) -> "PJTWireMarker":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param point2d_id: Identifier for the point 2D.
        :type point2d_id: int
        :param point3d_id: Identifier for the point 3D.
        :type point3d_id: int
        :param wire_id: Identifier for the wire.
        :type wire_id: int
        :param part_id: Identifier for the part.
        :type part_id: int
        :param label: Value for ``label``.
        :type label: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`PJTWireMarker`
        """

        db_id = PJTTableBase.insert(self, point2d_id=point2d_id, point3d_id=point3d_id,
                                    wire_id=wire_id, part_id=part_id, label=label)

        return PJTWireMarker(self, db_id, self.project_id)


class PJTWireMarker(PJTEntryBase, Position2DMixin, Position3DMixin, PartMixin,
                    Visible3DMixin, Visible2DMixin, NameMixin, NotesMixin, SmoothMixin):
    """Represent a PJT wire marker in :mod:`harness_designer.database.project_db.pjt_wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: PJTWireMarkersTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """
        packet = {
            'pjt_wire_markers': [self.db_id],
            'pjt_points3d': [self.position3d_id],
            'pjt_points2d': [self.position2d_id]
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)
        self.merge_packet_data(self.wire.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_wire_marker_obj.WireMarker":
        """Return the object.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: :class:`_wire_marker_obj.WireMarker`
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

    def set_object(self, obj: "_wire_marker_obj.WireMarker"):
        """Set the object.

        UNKNOWN details are inferred from the callable name and signature.

        :param obj: Object instance to operate on.
        :type obj: :class:`_wire_marker_obj.WireMarker`
        """
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTWireMarkersTable:
        """Return the table.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`PJTWireMarkersTable`
        """
        return self._table

    _stored_wire: "_pjt_wire.PJTWire" = None

    @property
    def wire(self) -> "_pjt_wire.PJTWire":
        """Return the wire.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_pjt_wire.PJTWire`
        """
        if self._stored_wire is None and self._obj is not None:
            wire_id = self.wire_id
            self._stored_wire = self._table.db.pjt_wires_table[wire_id]
            self._stored_wire.add_object(self._obj())

        return self._stored_wire

    @property
    def wire_id(self) -> int:
        """Return the wire ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('wire_id', id=self._db_id)[0][0]

    @wire_id.setter
    def wire_id(self, value: int):
        """Set the wire ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_wire = None
        self._table.update(self._db_id, wire_id=value)
        self._populate('wire_id')

    _stored_part: "_wire_marker.WireMarker" = None

    @property
    def part(self) -> "_wire_marker.WireMarker":
        """Return the part.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_wire_marker.WireMarker`
        """
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id
            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.wire_markers_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    @property
    def label(self) -> str:
        """Return the label.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('label', id=self._db_id)[0][0]

    @label.setter
    def label(self, value: str):
        """Set the label.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, label=value)
        self._populate('label')


class PJTWireMarkerControl(QTabWidget):
    """Represent a PJT wire marker control in :mod:`harness_designer.database.project_db.pjt_wire_marker`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def set_obj(self, db_obj: PJTWireMarker):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PJTWireMarker`
        """
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.note_ctrl.set_obj(db_obj)
        self.smooth_ctrl.set_obj(db_obj)
        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)
        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.wire_marker_ctrl.set_obj(None)
        else:
            self.wire_marker_ctrl.set_obj(db_obj.part)

    def __init__(self, parent):
        """Initialise the :class:`PJTWireMarkerControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PJTWireMarker = None

        QTabWidget.__init__(self, parent)
        self.setTabPosition(QTabWidget.TabPosition.North)
        self.setUsesScrollButtons(True)

        general_page = _prop_ctrls.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)
        self.smooth_ctrl = SmoothControl(general_page)

        position_page = _prop_ctrls.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        visible_page = _prop_ctrls.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        part_page = _prop_ctrls.Category(self, 'Part')
        self.wire_marker_ctrl = _wire_marker.WireMarkerControl(part_page)

        for page in (
            general_page,
            position_page,
            visible_page,
            part_page
        ):
            self.addTab(page, page.GetLabel())
            page.Realize()
