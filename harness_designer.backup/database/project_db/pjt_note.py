from typing import TYPE_CHECKING, Iterable as _Iterable

import uuid

from . import PJTEntryBase, PJTTableBase

from ...geometry import angle as _angle

if TYPE_CHECKING:
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_point3d as _pjt_point3d


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


class PJTNote(PJTEntryBase):
    _table: PJTNotesTable = None
    _angle2d_id: str = None
    _angle3d_id: str = None

    @property
    def table(self) -> PJTNotesTable:
        return self._table

    @property
    def point2d(self) -> "_pjt_point2d.PJTPoint2D":
        db_id = self.point2d_id
        if db_id is None:
            return None

        return self._table.db.pjt_points2d_table[db_id]

    @property
    def point2d_id(self) -> int:
        return self._table.select('point2d_id', id=self._db_id)[0][0]

    @point2d_id.setter
    def point2d_id(self, value: int):
        self._table.update(self._db_id, point2d_id=value)
        self._process_callbacks()

    def _update_angle2d(self, angle: _angle.Angle):
        self._table.update(self._db_id, angle2d=str(angle.as_quat.tolist()))

    @property
    def angle2d(self) -> _angle.Angle:
        quat = eval(self._table.select('angle2d', id=self._db_id)[0][0])
        if self._angle2d_id is None:
            self._angle2d_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, db_id=self._angle2d_id)
        angle.bind(self._update_angle2d)
        return angle

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
    def point3d(self) -> "_pjt_point3d.PJTPoint3D":
        db_id = self.point3d_id
        if db_id is None:
            return None

        return self._table.db.pjt_points3d_table[db_id]

    @property
    def point3d_id(self) -> int:
        return self._table.select('point3d_id', id=self._db_id)[0][0]

    @point3d_id.setter
    def point3d_id(self, value: int):
        self._table.update(self._db_id, point3d_id=value)
        self._process_callbacks()

    def _update_angle3d(self, angle: _angle.Angle):
        self._table.update(self._db_id, angle3d=str(angle.as_quat.tolist()))

    @property
    def angle3d(self) -> _angle.Angle:
        quat = eval(self._table.select('angle3d', id=self._db_id)[0][0])
        if self._angle3d_id is None:
            self._angle3d_id = str(uuid.uuid4())

        angle = _angle.Angle.from_quat(quat, db_id=self._angle3d_id)
        angle.bind(self._update_angle3d)
        return angle

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
