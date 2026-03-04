
from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase

from ...geometry import angle as _angle
from .mixins import Angle3DMixin, Position3DMixin, PartMixin, NameMixin, Visible3DMixin

if TYPE_CHECKING:
    from . import pjt_transition_branch as _pjt_transition_branch
    from ..global_db import transition as _transition

    from ...objects import transition as _transition_obj


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


class PJTTransition(PJTEntryBase, Angle3DMixin, Position3DMixin, PartMixin,
                    NameMixin, Visible3DMixin):

    _table: PJTTransitionsTable = None

    def get_object(self) -> "_transition_obj.Transition":
        return self._obj

    def set_object(self, obj: "_transition_obj.Transition"):
        self._obj = obj

    @property
    def table(self) -> PJTTransitionsTable:
        return self._table

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
    def part(self) -> "_transition.Transition":
        part_id = self.part_id
        if part_id is None:
            return None
        
        return self._table.db.global_db.transitions_table[part_id]
