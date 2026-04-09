
from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import Position3DMixin, PartMixin
from ...ui.editor_obj import prop_grid as _prop_grid


if TYPE_CHECKING:
    from . import pjt_transition as _pjt_transition
    from . import pjt_wire as _pjt_wire
    from . import pjt_concentric as _pjt_concentric
    from . import pjt_bundle as _pjt_bundle
    from ..global_db import transition_branch as _transition_branch


class PJTTransitionBranchesTable(PJTTableBase):
    __table_name__ = 'pjt_transition_branches'

    def _table_needs_update(self) -> bool:
        from ..create_database import transition_branches

        return transition_branches.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import transition_branches

        transition_branches.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import transition_branches

        transition_branches.pjt_table.update_fields(self)

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
               branch_id: int, diameter: float) -> "PJTTransitionBranch":

        if branch_id < 1 or branch_id > 6:
            raise RuntimeError('sanity check')

        db_id = PJTTableBase.insert(self, transition_id=transition_id, point_id=point_id,
                                    branch_id=branch_id, diameter=float(diameter))

        return PJTTransitionBranch(self, db_id, self.project_id)


class PJTTransitionBranch(PJTEntryBase, Position3DMixin, PartMixin):
    _table: PJTTransitionBranchesTable = None

    def build_monitor_packet(self):

        packet = {
            'pjt_transition_branches': [self.db_id],
            'pjt_points3d': [self.position3d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    @property
    def table(self) -> PJTTransitionBranchesTable:
        return self._table

    @property
    def wires(self) -> "_pjt_wire.PJTWire":
        res = []

        for layer in self.concentric.layers:
            res.extend(layer.wires)

        return res

    @property
    def bundle(self) -> "_pjt_bundle.PJTBundle":
        position_id = self.position3d_id
        bundle_ids = self.table.db.pjt_bundles_table.select('id', start_point3d_id=position_id)[0][0]
        if not bundle_ids:
            bundle_ids = self.table.db.pjt_bundles_table.select('id', stop_point3d_id=position_id)[0][0]

        if not bundle_ids:
            return None

        return self.table.db.pjt_bundles_table[bundle_ids[0][0]]

    @property
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        concentric_id = self.table.db.pjt_concentrics_table.select('id', transition_branch_id=self.db_id)[0][0]

        if concentric_id is None:
            return None

        return self.table.db.pjt_concentrics_table[concentric_id]

    @property
    def transition(self) -> "_pjt_transition.PJTTransition":
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
    def branch_id(self) -> int:
        return self._table.select('branch_id', id=self._db_id)[0][0]

    @branch_id.setter
    def branch_id(self, value: int):
        self._table.update(self._db_id, branch_id=value)
        self._process_callbacks()

    @property
    def diameter(self) -> float:
        return self._table.select('diameter', id=self._db_id)[0][0]

    @diameter.setter
    def diameter(self, value: float):
        self._table.update(self._db_id, diameter=value)
        self._process_callbacks()

    _stored_part: "_transition_branch.TransitionBranch" = None

    def reload_from_db(self):
        self.transition.update_objects()

    @property
    def part(self) -> "_transition_branch.TransitionBranch":
        if self._stored_part is None:
            part_id = self.part_id
            self._stored_part = self._table.db.global_db.transition_branches_table[part_id]
            self._stored_part.add_object(self)

        return self._stored_part

    @property
    def propgrid(self) -> tuple[_prop_grid.Category, _prop_grid.Category]:
        group = _prop_grid.Category('Project')

        position_prop = self._position3d_propgrid
        diameter_prop = _prop_grid.FloatProperty('Diameter', 'diameter', self.diameter,
                                                 min_value=0.01, max_value=99.99, increment=0.01, units='mm')

        group.Append(diameter_prop)
        group.Append(position_prop)

        part_prop = self._part_propgrid

        return group, part_prop
