
from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
import wx

from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    Position3DMixin, Position3DControl,
    Position2DMixin, Position2DControl,
    Visible3DMixin, Visible2DControl,
    Visible2DMixin, Visible3DControl
)


if TYPE_CHECKING:
    from . import pjt_wire as _pjt_wire

    from ...objects import wire_layout as _wire_layout_obj


class PJTWireLayoutsTable(PJTTableBase):
    __table_name__ = 'pjt_wire_layouts'

    _control: "PJTWireLayoutControl" = None

    @property
    def control(self) -> "PJTWireLayoutControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTWireLayoutControl(mainframe)
        cls._control.Show(False)

    def _table_needs_update(self) -> bool:
        from ..create_database import wire_layouts

        return wire_layouts.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import wire_layouts

        wire_layouts.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import wire_layouts

        wire_layouts.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTWireLayout"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireLayout(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWireLayout":
        if isinstance(item, int):
            if item in self:
                return PJTWireLayout(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, point_id: int) -> "PJTWireLayout":
        db_id = PJTTableBase.insert(self, point_id=point_id)
        return PJTWireLayout(self, db_id, self.project_id)


class PJTWireLayout(PJTEntryBase, Position3DMixin, Position2DMixin,
                    Visible3DMixin, Visible2DMixin):

    _table: PJTWireLayoutsTable = None

    def build_monitor_packet(self):
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
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_wire_layout_obj.WireLayout"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def attached_wires(self) -> list["_pjt_wire.PJTWire"]:
        res = []
        point_id = self.position3d_id
        db_ids = self._table.db.pjt_wires_table.select(
            "id", OR=True, start_point3d_id=point_id, stop_point3d_id=point_id)
        for db_id in db_ids:
            res.append(self._table.db.pjt_wires_table[db_id[0]])

        return res

    @property
    def table(self) -> PJTWireLayoutsTable:
        return self._table


class PJTWireLayoutControl(wx.Notebook):

    def set_obj(self, db_obj: PJTWireLayout):
        self.db_obj = db_obj

        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)
        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

    def __init__(self, parent):
        self.db_obj: PJTWireLayout = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        position_page = _prop_grid.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        for page in (
            position_page,
            visible_page,
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
