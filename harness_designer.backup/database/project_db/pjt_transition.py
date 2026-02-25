
from typing import TYPE_CHECKING, Iterable as _Iterable

import uuid

from . import PJTEntryBase, PJTTableBase

from ...geometry import angle as _angle

if TYPE_CHECKING:
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_transition_branch as _pjt_transition_branch
    from ..global_db import transition as _transition


class PJTTransitionsTable(PJTTableBase):
    __table_name__ = 'pjt_transitions'

    def __iter__(self) -> _Iterable["PJTTransition"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTransition(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTTransition":
        if isinstance(item, int):
            if item in self:
                return PJTTransition(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, center_id: int, angle: _angle.Angle, name: str) -> "PJTTransition":

        db_id = PJTTableBase.insert(self, part_id=part_id, center_id=center_id,
                                    angle=str(list(angle.as_float)), name=name)

        return PJTTransition(self, db_id, self.project_id)


class PJTTransition(PJTEntryBase):
    _table: PJTTransitionsTable = None
    _angle_id: str = None

    @property
    def table(self) -> PJTTransitionsTable:
        return self._table

    @property
    def point3d(self) -> "_pjt_point3d.PJTPoint3D":
        point3d_id = self.point3d_id
        return self._table.db.pjt_points3d_table[point3d_id]

    @property
    def point3d_id(self) -> int:
        return self._table.select('point3d_id', id=self._db_id)[0][0]

    @point3d_id.setter
    def point3d_id(self, value: int):
        self._table.update(self._db_id, point3d_id=value)
        self._process_callbacks()

    @property
    def branch1(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        db_id = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=1)[0][0]

        return self.table.db.pjt_transition_branches_table[db_id]

    @property
    def branch2(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=2)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch3(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=3)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch4(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=4)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch5(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=5)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def branch6(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=6)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

    @property
    def name(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @name.setter
    def name(self, value: str):
        self._table.update(self._db_id, name=value)
        self._process_callbacks()

    def __update_angle(self, angle: _angle.Angle):
        self._table.update(self._db_id, quat=str(angle.as_quat))
        self._process_callbacks()

    @property
    def angle3d(self) -> _angle.Angle:
        if self._angle_id is None:
            self._angle_id = str(uuid.uuid4())

        quat = eval(self._table.select('quat', id=self._db_id)[0][0])
        angle = _angle.Angle.from_quat(quat, db_id=self._angle_id)
        angle.bind(self.__update_angle)
        return angle

    @property
    def part(self) -> "_transition.Transition":
        part_id = self.part_id
        if part_id is None:
            return None
        
        return self._table.db.global_db.transitions_table[part_id]

    @property
    def part_id(self) -> int:
        return self._table.select('part_id', id=self._db_id)[0][0]

    @part_id.setter
    def part_id(self, value: int):
        self._table.update(self._db_id, part_id=value)
        self._process_callbacks()
