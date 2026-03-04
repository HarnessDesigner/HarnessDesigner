from typing import Iterable as _Iterable, TYPE_CHECKING


from . import PJTEntryBase, PJTTableBase

from .mixins import (Angle3DMixin, Angle2DMixin, Position3DMixin, Position2DMixin,
                     Visible3DMixin, Visible2DMixin)


if TYPE_CHECKING:
    from ...objects import note as _note_obj


class PJTNotesTable(PJTTableBase):
    __table_name__ = 'pjt_notes'

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


class PJTNote(PJTEntryBase, Angle3DMixin, Angle2DMixin,
              Position3DMixin, Position2DMixin, Visible3DMixin, Visible2DMixin):

    _table: PJTNotesTable = None

    def get_object(self) -> "_note_obj.Note":
        return self._obj

    def set_object(self, obj: "_note_obj.Note"):
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
    def note(self) -> str:
        return self._table.select('note', id=self._db_id)[0][0]

    @note.setter
    def note(self, value: str):
        self._table.update(self._db_id, note=value)
        self._process_callbacks()
