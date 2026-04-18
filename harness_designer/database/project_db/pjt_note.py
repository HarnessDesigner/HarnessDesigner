from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref
import wx
import build123d

from ...ui.editor_obj import prop_grid as _prop_grid
from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (
    Angle3DMixin, Angle3DControl,
    Angle2DMixin, Angle2DControl,
    Position3DMixin, Position3DControl,
    Position2DMixin, Position2DControl,
    Visible3DMixin, Visible3DControl,
    Visible2DMixin, Visible2DControl,
    NotesMixin, NotesControl
)


if TYPE_CHECKING:
    from ...objects import note as _note_obj


class PJTNotesTable(PJTTableBase):
    __table_name__ = 'pjt_notes'

    _control: "PJTNoteControl" = None

    @property
    def control(self) -> "PJTNoteControl":
        if self._control is None:
            raise RuntimeError('sanity check')

        return self._control

    @classmethod
    def start_control(cls, mainframe):
        cls._control = PJTNoteControl(mainframe)
        cls._control.Show(False)

    def _table_needs_update(self) -> bool:
        from ..create_database import notes

        return notes.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import notes

        notes.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import notes

        notes.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTNote"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTNote(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTNote":
        if isinstance(item, int):
            if item in self:
                return PJTNote(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, point2d_id: int | None, point3d_id: int | None,
               note: str, size: int) -> "PJTNote":

        db_id = PJTTableBase.insert(self, point2d_id=point2d_id,
                                    point3d_id=point3d_id, note=note, size=size)

        return PJTNote(self, db_id, self.project_id)


class PJTNote(PJTEntryBase, Angle3DMixin, Angle2DMixin, NotesMixin,
              Position3DMixin, Position2DMixin, Visible3DMixin, Visible2DMixin):

    _table: PJTNotesTable = None

    def build_monitor_packet(self):

        packet = {
            'pjt_notes': [self.db_id],
            'pjt_points3d': [self.position3d_id],
            'pjt_points2d': [self.position2d_id],
        }

        return packet

    def get_object(self) -> "_note_obj.Note":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_note_obj.Note"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTNotesTable:
        return self._table

    @property
    def size2d(self) -> int:
        return self._table.select('size2d', id=self._db_id)[0][0]

    @size2d.setter
    def size2d(self, value: int):
        self._table.update(self._db_id, size2d=value)
        self._populate('size2d')

    @property
    def h_align2d(self) -> int:
        return self._table.select('h_align2d', id=self._db_id)[0][0]

    @h_align2d.setter
    def h_align2d(self, value: int):
        self._table.update(self._db_id, h_align2d=value)
        self._populate('h_align2d')

    @property
    def v_align2d(self) -> int:
        return self._table.select('v_align2d', id=self._db_id)[0][0]

    @v_align2d.setter
    def v_align2d(self, value: int):
        self._table.update(self._db_id, v_align2d=value)
        self._populate('v_align2d')

    @property
    def style2d(self) -> int:
        return self._table.select('style2d', id=self._db_id)[0][0]

    @style2d.setter
    def style2d(self, value: int):
        self._table.update(self._db_id, style2d=value)
        self._populate('style2d')

    @property
    def is_visible2d(self) -> bool:
        return bool(self._table.select('is_visible2d', id=self._db_id)[0][0])

    @is_visible2d.setter
    def is_visible2d(self, value: bool):
        self._table.update(self._db_id, is_visible2d=int(value))
        self._populate('is_visible2d')

    @property
    def size3d(self) -> float:
        return self._table.select('size3d', id=self._db_id)[0][0]

    @size3d.setter
    def size3d(self, value: float):
        self._table.update(self._db_id, size3d=value)
        self._populate('size3d')

    @property
    def h_align3d(self) -> int:
        return self._table.select('h_align3d', id=self._db_id)[0][0]

    @h_align3d.setter
    def h_align3d(self, value: int):
        self._table.update(self._db_id, h_align3d=value)
        self._populate('h_align3d')

    @property
    def v_align3d(self) -> int:
        return self._table.select('v_align3d', id=self._db_id)[0][0]

    @v_align3d.setter
    def v_align3d(self, value: int):
        self._table.update(self._db_id, v_align3d=value)
        self._populate('v_align3d')

    @property
    def style3d(self) -> int:
        return self._table.select('style3d', id=self._db_id)[0][0]

    @style3d.setter
    def style3d(self, value: int):
        self._table.update(self._db_id, style3d=value)
        self._populate('style3d')

    @property
    def is_visible3d(self) -> bool:
        return bool(self._table.select('is_visible3d', id=self._db_id)[0][0])

    @is_visible3d.setter
    def is_visible3d(self, value: bool):
        self._table.update(self._db_id, is_visible3d=int(value))
        self._populate('is_visible3d')


class PJTNoteControl(wx.Notebook):

    def set_obj(self, db_obj: PJTNote):
        if self.db_obj is not None:
            if self.db_obj.is_visible2d:
                self.align_2d_ctrl.SetValue(build123d.TextAlign.LEFT)
                self.style_2d_ctrl.SetValue(build123d.FontStyle.REGULAR)

            if self.db_obj.is_visible3d:
                self.align_3d_ctrl.SetValue(build123d.TextAlign.LEFT)
                self.style_3d_ctrl.SetValue(build123d.FontStyle.REGULAR)

        self.db_obj = db_obj

        self.note_ctrl.set_obj(db_obj)

        self.angle2d_ctrl.set_obj(db_obj)
        self.angle3d_ctrl.set_obj(db_obj)

        self.position2d_ctrl.set_obj(db_obj)
        self.position3d_ctrl.set_obj(db_obj)

        self.visible2d_ctrl.set_obj(db_obj)
        self.visible3d_ctrl.set_obj(db_obj)

        if db_obj is None:
            self.align_2d_ctrl.Enable(False)
            self.style_2d_ctrl.Enable(False)
            self.align_3d_ctrl.Enable(False)
            self.style_3d_ctrl.Enable(False)
        else:
            if db_obj.is_visible2d:
                self.align_2d_ctrl.SetLabels(['Left', 'Center', 'Right'])
                self.align_2d_ctrl.SetItems(
                    [build123d.TextAlign.LEFT, build123d.TextAlign.CENTER,
                     build123d.TextAlign.RIGHT])

                self.align_2d_ctrl.Show(True)
                self.align_2d_ctrl.SetValue(db_obj.h_align2d)

                self.style_2d_ctrl.SetLabels(['Normal', 'Bold', 'Italic', 'Bold Italic'])
                self.style_2d_ctrl.SetItems(
                    [build123d.FontStyle.REGULAR, build123d.FontStyle.BOLD,
                     build123d.FontStyle.ITALIC, build123d.FontStyle.BOLDITALIC])

                self.style_2d_ctrl.Show(True)
                self.style_2d_ctrl.SetValue(db_obj.h_align3d)
            else:
                self.align_2d_ctrl.Hide()
                self.style_2d_ctrl.Hide()

            if db_obj.is_visible3d:
                self.align_3d_ctrl.SetLabels(['Left', 'Center', 'Right'])
                self.align_3d_ctrl.SetItems(
                    [build123d.TextAlign.LEFT, build123d.TextAlign.CENTER,
                     build123d.TextAlign.RIGHT])

                self.align_3d_ctrl.Show(True)
                self.align_3d_ctrl.SetValue(db_obj.h_align3d)

                self.style_3d_ctrl.SetLabels(['Normal', 'Bold', 'Italic', 'Bold Italic'])
                self.style_3d_ctrl.SetItems(
                    [build123d.FontStyle.REGULAR, build123d.FontStyle.BOLD,
                     build123d.FontStyle.ITALIC, build123d.FontStyle.BOLDITALIC])

                self.style_3d_ctrl.Show(True)
                self.style_3d_ctrl.SetValue(db_obj.h_align3d)
            else:
                self.align_3d_ctrl.Hide()
                self.style_3d_ctrl.Hide()

    def _on_align2d(self, evt):
        value = evt.GetValue()
        self.db_obj.h_align2d = value

    def _on_align3d(self, evt):
        value = evt.GetValue()
        self.db_obj.h_align3d = value

    def _on_style2d(self, evt):
        value = evt.GetValue()
        self.db_obj.style2d = value

    def _on_style3d(self, evt):
        value = evt.GetValue()
        self.db_obj.style3d = value

    def __init__(self, parent):
        self.db_obj: PJTNote = None

        wx.Notebook.__init__(self, parent, wx.ID_ANY, style=wx.NB_TOP | wx.NB_MULTILINE)

        general_page = _prop_grid.Category(self, 'General')
        self.note_ctrl = NotesControl(general_page)

        style_page = _prop_grid.Category(self, 'Style')
        self.style_2d_ctrl = _prop_grid.EnumProperty(style_page, '2D Style')
        self.style_3d_ctrl = _prop_grid.EnumProperty(style_page, '3D Style')

        align_page = _prop_grid.Category(self, 'Align')
        self.align_2d_ctrl = _prop_grid.EnumProperty(align_page, '2D Align')
        self.align_3d_ctrl = _prop_grid.EnumProperty(align_page, '3D Align')

        self.style_2d_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_style2d)
        self.style_3d_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_style3d)

        self.align_2d_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_align2d)
        self.align_3d_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_align3d)

        angle_page = _prop_grid.Category(self, 'Angle')
        self.angle2d_ctrl = Angle2DControl(angle_page)
        self.angle3d_ctrl = Angle3DControl(angle_page)

        position_page = _prop_grid.Category(self, 'Position')
        self.position2d_ctrl = Position2DControl(position_page)
        self.position3d_ctrl = Position3DControl(position_page)

        visible_page = _prop_grid.Category(self, 'Visible')
        self.visible2d_ctrl = Visible2DControl(visible_page)
        self.visible3d_ctrl = Visible3DControl(visible_page)

        for page in (
            general_page,
            angle_page,
            position_page,
            visible_page,
            style_page,
            align_page
        ):
            self.AddPage(page, page.GetLabel())
            page.Realize()
