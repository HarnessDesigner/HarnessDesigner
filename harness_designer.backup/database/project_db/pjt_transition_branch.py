
from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase
from ...wrappers.decimal import Decimal as _decimal

if TYPE_CHECKING:
    from . import pjt_transition as _pjt_transition
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_concentric as _pjt_concentric


class PJTTransitionBranchesTable(PJTTableBase):
    __table_name__ = 'pjt_transition_branches'

    def __iter__(self) -> _Iterable["PJTTransitionBranch"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTTransitionBranch(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTTransitionBranch":
        if isinstance(item, int):
            if item in self:
                return PJTTransitionBranch(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, transition_id: int, point_id: int,
               branch_id: int, diameter: _decimal) -> "PJTTransitionBranch":

        if branch_id < 1 or branch_id > 6:
            raise RuntimeError('sanity check')

        db_id = PJTTableBase.insert(self, transition_id=transition_id, point_id=point_id,
                                    branch_id=branch_id, diameter=float(diameter))

        return PJTTransitionBranch(self, db_id, self.project_id)


class PJTTransitionBranch(PJTEntryBase):
    _table: PJTTransitionBranchesTable = None

    @property
    def table(self) -> PJTTransitionBranchesTable:
        return self._table

    @property
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        concentric_id = self.table.db.pjt_concentrics_table.select('id', transition_branch_id=self.db_id)[0][0]

        if concentric_id is None:
            return None

        return self.table.db.pjt_concentrics_table[concentric_id]

    @property
    def Transition(self) -> "_pjt_transition.PJTTransition":
        transition_id = self.transition_id

        return self._table.db.pjt_transitions_table[transition_id]

    @property
    def transition_id(self) -> int:
        return self._table.select('transition_id', id=self._db_id)[0][0]

    @transition_id.setter
    def transition_id(self, value: int):
        self._table.update(self._db_id, transition_id=value)
        self._process_callbacks()

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
    def branch_id(self) -> int:
        return self._table.select('branch_id', id=self._db_id)[0][0]

    @branch_id.setter
    def branch_id(self, value: int):
        self._table.update(self._db_id, branch_id=value)
        self._process_callbacks()

    @property
    def diameter(self) -> _decimal:
        return _decimal(self._table.select('diameter', id=self._db_id)[0][0])

    @diameter.setter
    def diameter(self, value: _decimal):
        self._table.update(self._db_id, diameter=float(value))
        self._process_callbacks()
