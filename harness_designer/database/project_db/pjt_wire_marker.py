from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from .pjt_bases import PJTEntryBase, PJTTableBase
from ..global_db import wire_marker as _wire_marker
from .mixins import (
    Position2DMixin, Position2DControl,
    Position3DMixin, Position3DControl,
    PartMixin,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl
)

if TYPE_CHECKING:
    from . import pjt_wire as _pjt_wire

    from ...objects import wire_marker as _wire_marker_obj


class PJTWireMarkersTable(PJTTableBase):
    __table_name__ = 'pjt_wire_markers'

    _control: "PJTWireMarkerControl" = None

    @property
    def control(self) -> "PJTWireMarkerControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTWireMarkerControl(mainframe)
        cls._control.Show(False)

    def _table_needs_update(self) -> bool:
        from ..create_database import wire_markers

        return wire_markers.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import wire_markers

        wire_markers.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import wire_markers

        wire_markers.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTWireMarker"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireMarker(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWireMarker":
        if isinstance(item, int):
            if item in self:
                return PJTWireMarker(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, point2d_id: int, point3d_id: int,
               wire_id: int, part_id: int, label: str) -> "PJTWireMarker":

        db_id = PJTTableBase.insert(self, point2d_id=point2d_id, point3d_id=point3d_id,
                                    wire_id=wire_id, part_id=part_id, label=label)

        return PJTWireMarker(self, db_id, self.project_id)


class PJTWireMarker(PJTEntryBase, Position2DMixin, Position3DMixin, PartMixin,
                    Visible3DMixin, Visible2DMixin, NameMixin, NotesMixin):
    _table: PJTWireMarkersTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_wire_markers': [self.db_id],
            'pjt_points3d': [self.position3d_id],
            'pjt_points2d': [self.position2d_id]
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)
        self.merge_packet_data(self.wire.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_wire_marker_obj.WireMarker":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_wire_marker_obj.WireMarker"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTWireMarkersTable:
        return self._table

    _stored_wire: "_pjt_wire.PJTWire" = None

    @property
    def wire(self) -> "_pjt_wire.PJTWire":
        if self._stored_wire is None and self._obj is not None:
            wire_id = self.wire_id
            self._stored_wire = self._table.db.pjt_wires_table[wire_id]
            self._stored_wire.add_object(self._obj())

        return self._stored_wire

    @property
    def wire_id(self) -> int:
        return self._table.select('wire_id', id=self._db_id)[0][0]

    @wire_id.setter
    def wire_id(self, value: int):
        self._stored_wire = None
        self._table.update(self._db_id, wire_id=value)
        self._populate('wire_id')

    _stored_part: "_wire_marker.WireMarker" = None

    @property
    def part(self) -> "_wire_marker.WireMarker":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id
            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.wire_markers_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    @property
    def label(self) -> str:
        return self._table.select('label', id=self._db_id)[0][0]

    @label.setter
    def label(self, value: str):
        self._table.update(self._db_id, label=value)
        self._populate('label')


class PJTWireMarkerControl(wx.Notebook):

    def set_obj(self, db_obj: PJTWireMarker):
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.note_ctrl.set_obj(db_obj)
        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)
        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.wire_marker_ctrl.set_obj(None)
        else:
            self.wire_marker_ctrl.set_obj(db_obj.part)

    def __init__(self, parent):
        self.db_obj: PJTWireMarker = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)

        position_page = _prop_grid.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        part_page = _prop_grid.Category(self, 'Part')
        self.wire_marker_ctrl = _wire_marker.WireMarkerControl(part_page)

        for page in (
            general_page,
            position_page,
            visible_page,
            part_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
