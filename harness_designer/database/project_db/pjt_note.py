from typing import Iterable as _Iterable, TYPE_CHECKING

import weakref
from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase

from .mixins import (Angle3DMixin, Angle2DMixin, Position3DMixin, Position2DMixin,
                     Visible3DMixin, Visible2DMixin, NotesMixin)


if TYPE_CHECKING:
    from ...objects import note as _note_obj


class PJTNotesTable(PJTTableBase):
    __table_name__ = 'pjt_notes'

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
        self._process_callbacks()

    @property
    def h_align2d(self) -> int:
        return self._table.select('h_align2d', id=self._db_id)[0][0]

    @h_align2d.setter
    def h_align2d(self, value: int):
        self._table.update(self._db_id, h_align2d=value)
        self._process_callbacks()

    @property
    def v_align2d(self) -> int:
        return self._table.select('v_align2d', id=self._db_id)[0][0]

    @v_align2d.setter
    def v_align2d(self, value: int):
        self._table.update(self._db_id, v_align2d=value)
        self._process_callbacks()

    @property
    def style2d(self) -> int:
        return self._table.select('style2d', id=self._db_id)[0][0]

    @style2d.setter
    def style2d(self, value: int):
        self._table.update(self._db_id, style2d=value)
        self._process_callbacks()

    @property
    def is_visible2d(self) -> bool:
        return bool(self._table.select('is_visible2d', id=self._db_id)[0][0])

    @is_visible2d.setter
    def is_visible2d(self, value: bool):
        self._table.update(self._db_id, is_visible2d=int(value))
        self._process_callbacks()

    @property
    def size3d(self) -> float:
        return self._table.select('size3d', id=self._db_id)[0][0]

    @size3d.setter
    def size3d(self, value: float):
        self._table.update(self._db_id, size3d=value)
        self._process_callbacks()

    @property
    def h_align3d(self) -> int:
        return self._table.select('h_align3d', id=self._db_id)[0][0]

    @h_align3d.setter
    def h_align3d(self, value: int):
        self._table.update(self._db_id, h_align3d=value)
        self._process_callbacks()

    @property
    def v_align3d(self) -> int:
        return self._table.select('v_align3d', id=self._db_id)[0][0]

    @v_align3d.setter
    def v_align3d(self, value: int):
        self._table.update(self._db_id, v_align3d=value)
        self._process_callbacks()

    @property
    def style3d(self) -> int:
        return self._table.select('style3d', id=self._db_id)[0][0]

    @style3d.setter
    def style3d(self, value: int):
        self._table.update(self._db_id, style3d=value)
        self._process_callbacks()

    @property
    def is_visible3d(self) -> bool:
        return bool(self._table.select('is_visible3d', id=self._db_id)[0][0])

    @is_visible3d.setter
    def is_visible3d(self, value: bool):
        self._table.update(self._db_id, is_visible3d=int(value))
        self._process_callbacks()

    @property
    def propgrid(self) -> tuple[_prop_grid.Category]:
        import build123d

        group = _prop_grid.Category('Project')

        notes_prop = self._notes_propgrid

        angle_prop = _prop_grid.Category('Angle')
        angle2d_prop = self._angle2d_propgrid
        angle3d_prop = self._angle3d_propgrid
        angle2d_prop.SetLabel('2D')
        angle3d_prop.SetLabel('3D')
        angle_prop.Append(angle2d_prop)
        angle_prop.Append(angle3d_prop)

        position_prop = _prop_grid.Category('Position')
        position2d_prop = self._position2d_propgrid
        position3d_prop = self._position3d_propgrid
        position2d_prop.SetLabel('2D')
        position3d_prop.SetLabel('3D')
        position_prop.Append(position2d_prop)
        position_prop.Append(position3d_prop)

        visible_prop = _prop_grid.Category('Visible')
        visible2d_prop = self._visible2d_propgrid
        visible3d_prop = self._visible3d_propgrid
        visible_prop.Append(visible2d_prop)
        visible_prop.Append(visible3d_prop)

        # TODO: Create Enum Property

        style_prop = _prop_grid.Category('Style')
        style2d_prop = _prop_grid.EnumProperty(
            '2D', 'style2d', labels=['Normal', 'Bold', 'Italic', 'Bold Italic'],
            values=[build123d.FontStyle.REGULAR, build123d.FontStyle.BOLD,
                    build123d.FontStyle.ITALIC, build123d.FontStyle.BOLDITALIC],
            value=self.style2d)
        style3d_prop = _prop_grid.EnumProperty(
            '3D', 'style3d', labels=['Normal', 'Bold', 'Italic', 'Bold Italic'],
            values=[build123d.FontStyle.REGULAR, build123d.FontStyle.BOLD,
                    build123d.FontStyle.ITALIC, build123d.FontStyle.BOLDITALIC],
            value=self.style3d)
        style_prop.Append(style2d_prop)
        style_prop.Append(style3d_prop)

        align_prop = _prop_grid.Category('Align')
        h_align2d_prop = _prop_grid.EnumProperty(
            '2D', 'h_align2d', labels=['Left', 'Center', 'Right'],
            values=[build123d.TextAlign.LEFT, build123d.TextAlign.CENTER, build123d.TextAlign.RIGHT],
            value=self.h_align2d)
        h_align3d_prop = _prop_grid.EnumProperty(
            '3D', 'h_align3d', labels=['Left', 'Center', 'Right'],
            values=[build123d.TextAlign.LEFT, build123d.TextAlign.CENTER, build123d.TextAlign.RIGHT],
            value=self.h_align3d)
        align_prop.Append(h_align2d_prop)
        align_prop.Append(h_align3d_prop)

        size_prop = _prop_grid.Category('Size')
        size2d_prop = _prop_grid.FloatProperty(
            '2D', 'size2d', self.size2d,
            min_value=0.2, max_value=99.9, increment=0.1, units='mm')
        size3d_prop = _prop_grid.FloatProperty(
            '3D', 'size3d', self.size3d,
            min_value=0.2, max_value=99.9, increment=0.1, units='mm')
        size_prop.Append(size2d_prop)
        size_prop.Append(size3d_prop)

        group.Append(notes_prop)
        group.Append(angle_prop)
        group.Append(position_prop)
        group.Append(visible_prop)
        group.Append(style_prop)
        group.Append(align_prop)
        group.Append(size_prop)

        return (group,)
