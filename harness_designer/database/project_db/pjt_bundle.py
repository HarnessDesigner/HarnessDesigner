from typing import TYPE_CHECKING, Iterable as _Iterable, Union

import weakref

import wx

from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    PartMixin,
    StartStopPosition3DMixin, StartStopPosition3DControl,
    Visible3DMixin, Visible3DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl
)


if TYPE_CHECKING:
    from . import pjt_concentric as _pjt_concentric
    from . import pjt_bundle_layout as _pjt_bundle_layout
    from . import pjt_wire as _pjt_wire

    from ..global_db import bundle_cover as _bundle_cover

    from ...objects import bundle as _bundle_obj


class PJTBundlesTable(PJTTableBase):
    __table_name__ = 'pjt_bundles'

    _control: "PJTBundleControl" = None

    @property
    def control(self) -> "PJTBundleControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTBundleControl(mainframe)
        cls._control.Show(False)

    def _table_needs_update(self) -> bool:
        from ..create_database import bundle_covers

        return bundle_covers.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import bundle_covers

        bundle_covers.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import bundle_covers

        bundle_covers.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTBundle"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundle(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTBundle":
        if isinstance(item, int):
            if item in self:
                return PJTBundle(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int) -> "PJTBundle":
        db_id = PJTTableBase.insert(self, part_id=part_id)

        return PJTBundle(self, db_id, self.project_id)


class PJTBundle(PJTEntryBase, PartMixin, StartStopPosition3DMixin,
                Visible3DMixin, NameMixin, NotesMixin):
    _table: PJTBundlesTable = None

    def build_monitor_packet(self):
        packet = {
            'pjt_bundles': [self.db_id],
            'bundle_covers': [self.part_id],
            'pjt_points3d': [self.start_position3d_id, self.stop_position3d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_bundle_obj.Bundle":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_bundle_obj.Bundle"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTBundlesTable:
        return self._table

    @property
    def wires(self) -> list["_pjt_wire.PJTWire"]:
        res = []
        for layer in self.concentric.layers:
            res.extend(layer.wires)

        return res

    @property
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        concentric_id = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)[0][0]
        if concentric_id is None:
            return None

        return self.table.db.pjt_concentrics_table[concentric_id]

    @property
    def start_layout(self) -> Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.start_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    @property
    def stop_layout(self) -> Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.stop_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    @property
    def part(self) -> "_bundle_cover.BundleCover":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.bundle_covers_table[part_id]


class PJTBundleControl(wx.Notebook):

    def set_obj(self, db_obj: PJTBundle):
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.notes_ctrl.set_obj(db_obj)
        self.visible_ctrl.set_obj(db_obj)
        self.start_stop_ctrl.set_obj(db_obj)
        self.part_ctrl.set_obj(db_obj)

    def __init__(self, parent):
        self.db_obj: PJTBundle = None
        super().__init__(parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')

        self.name_ctrl = NameControl(general_page)
        self.notes_ctrl = NotesControl(general_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible_ctrl = Visible3DControl(visible_page)

        position_page = _prop_grid.Category(self, 'Position')
        self.start_stop_ctrl = StartStopPosition3DControl(position_page)

        part_page = _prop_grid.Category(self, 'Part')
        self.part_ctrl = _bundle_cover.BundleCoverControl(part_page)

        for page in (
            general_page,
            visible_page,
            position_page,
            part_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
