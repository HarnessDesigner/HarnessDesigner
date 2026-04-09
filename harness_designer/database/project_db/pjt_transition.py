
from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase

from ...geometry import angle as _angle
from .mixins import Angle3DMixin, Position3DMixin, PartMixin, NameMixin, Visible3DMixin

if TYPE_CHECKING:
    from . import pjt_transition_branch as _pjt_transition_branch
    from ..global_db import transition as _transition

    from ...objects import transition as _transition_obj


class PJTTransitionsTable(PJTTableBase):
    __table_name__ = 'pjt_transitions'

    def _table_needs_update(self) -> bool:
        from ..create_database import transitions

        return transitions.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import transitions

        transitions.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import transitions

        transitions.pjt_table.update_fields(self)

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

    def build_monitor_packet(self):

        packet = {
            'pjt_transitions': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }

        for branch in (
            self.branch1,
            self.branch2,
            self.branch3,
            self.branch4,
            self.branch5,
            self.branch6
        ):
            if branch is None:
                continue

            self.merge_packet_data(branch.build_monitor_packet(), packet)

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_transition_obj.Transition":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_transition_obj.Transition"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTTransitionsTable:
        return self._table

    @property
    def branch1(self) -> "_pjt_transition_branch.PJTTransitionBranch":
        db_ids = self.table.db.pjt_transition_branches_table.select(
            'id', transition_id=self.db_id, branch_id=1)

        if not db_ids:
            return None

        return self.table.db.pjt_transition_branches_table[db_ids[0][0]]

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

    _stored_part: "_transition.Transition" = None

    @property
    def part(self) -> "_transition.Transition":
        if self._stored_part is None and self._obj is not None:
            part_id = self.part_id

            if part_id is None:
                return None
        
            self._stored_part = self._table.db.global_db.transitions_table[part_id]
            self._stored_part.add_object(self._obj())

        return self._stored_part

    @property
    def propgrid(self) -> tuple[_prop_grid.Category, _prop_grid.Category]:
        group = _prop_grid.Category('Project')

        notes_prop = self._notes_propgrid
        name_prop = self._name_propgrid
        angle_prop = self._angle3d_propgrid
        position_prop = self._position3d_propgrid
        housing_prop = self._housing_propgrid
        visible_prop = self._visible3d_propgrid

        group.Append(name_prop)
        group.Append(notes_prop)
        group.Append(angle_prop)
        group.Append(position_prop)
        group.Append(visible_prop)
        group.Append(housing_prop)

        part_prop = self._part_propgrid

        return group, part_prop
