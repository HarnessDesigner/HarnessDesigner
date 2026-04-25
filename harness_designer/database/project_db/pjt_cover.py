from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
import wx

from ...ui.editor_obj import prop_grid as _prop_grid
from ..global_db import cover as _cover
from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Position3DMixin, Position3DControl,
    PartMixin,
    HousingMixin,
    Visible3DMixin, Visible3DControl,
    NameMixin, NameControl,
    NotesMixin, NotesControl
)


if TYPE_CHECKING:
    from ...objects import cover as _cover_obj


class PJTCoversTable(PJTTableBase):
    __table_name__ = 'pjt_covers'

    _control: "PJTCoverControl" = None

    @property
    def control(self) -> "PJTCoverControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTCoverControl(mainframe)
        cls._control.Show(False)

    def _table_needs_update(self) -> bool:
        from ..create_database import covers

        return covers.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import covers

        covers.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import covers

        covers.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTCover"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTCover(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTCover":
        if isinstance(item, int):
            if item in self:
                return PJTCover(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, position3d_id: int, housing_id: int | None) -> "PJTCover":
        db_id = PJTTableBase.insert(self, part_id=part_id, position3d_id=position3d_id, housing_id=housing_id)

        return PJTCover(self, db_id, self.project_id)


class PJTCover(PJTEntryBase, Angle3DMixin, Position3DMixin, NotesMixin,
               PartMixin, HousingMixin, Visible3DMixin, NameMixin):

    _table: PJTCoversTable = None

    def build_monitor_packet(self):

        packet = {
            'pjt_covers': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)
        self.merge_packet_data(self.housing.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_cover_obj.Cover":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_cover_obj.Cover"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTCoversTable:
        return self._table

    _stored_part: "_cover.Cover" = None

    @property
    def part(self) -> "_cover.Cover":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None

            self._stored_part = self._table.db.global_db.covers_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part


class PJTCoverControl(wx.Notebook):

    def set_obj(self, db_obj: PJTCover):
        self.db_obj = db_obj

        self.name_ctrl.set_obj(db_obj)
        self.note_ctrl.set_obj(db_obj)
        self.angle3d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.cover_ctrl.set_obj(None)
        else:
            self.cover_ctrl.set_obj(db_obj.part)

    def __init__(self, parent):
        self.db_obj: PJTCover = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')
        self.name_ctrl = NameControl(general_page)
        self.note_ctrl = NotesControl(general_page)

        angle_page = _prop_grid.Category(self, 'Angle')
        self.angle3d_ctrl = Angle3DControl(angle_page)

        position_page = _prop_grid.Category(self, 'Position')
        self.position3d_ctrl = Position3DControl(position_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible3d_ctrl = Visible3DControl(visible_page)

        part_page = _prop_grid.Category(self, 'Part')

        from ..global_db import cover as _cover  # NOQA

        self.cover_ctrl = _cover.CoverControl(part_page)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            part_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
