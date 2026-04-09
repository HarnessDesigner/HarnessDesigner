
from typing import TYPE_CHECKING, Iterable as _Iterable

import weakref
from ...ui.editor_obj import prop_grid as _prop_grid

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import (PartMixin, StartStopPosition3DMixin, Visible3DMixin,
                     Visible2DMixin, NameMixin, NotesMixin)
from ...geometry import point as _point


if TYPE_CHECKING:
    from . import pjt_point3d as _pjt_point3d
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_circuit as _pjt_circuit
    from . import pjt_wire as _pjt_wire

    from ..global_db import splice as _splice

    from ...objects import splice as _splice_obj


class PJTSplicesTable(PJTTableBase):
    __table_name__ = 'pjt_splices'

    def _table_needs_update(self) -> bool:
        from ..create_database import splices

        return splices.pjt_table.is_ok(self)

    def _add_table_to_db(self):
        from ..create_database import splices

        splices.pjt_table.add_to_db(self)

    def _update_table_in_db(self):
        from ..create_database import splices

        splices.pjt_table.update_fields(self)

    def __iter__(self) -> _Iterable["PJTSplice"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTSplice(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTSplice":
        if isinstance(item, int):
            if item in self:
                return PJTSplice(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int, circuit_id: int, start_point3d_id: int, stop_point3d_id: int,
               branch_point3d_id: int, point2d_id: int) -> "PJTSplice":

        db_id = PJTTableBase.insert(self, part_id=part_id, circuit_id=circuit_id,
                                    start_point3d_id=start_point3d_id, stop_point3d_id=stop_point3d_id,
                                    branch_point3d_id=branch_point3d_id, point2d_id=point2d_id)

        return PJTSplice(self, db_id, self.project_id)


class PJTSplice(PJTEntryBase, PartMixin, StartStopPosition3DMixin,
                Visible3DMixin, Visible2DMixin, NameMixin, NotesMixin):

    _table: PJTSplicesTable = None

    def build_monitor_packet(self):

        packet = {
            'pjt_cavities': [self.db_id],
            'cavities': [self.part_id],
            'pjt_points3d': [self.start_position3d_id, self.stop_position3d_id, self.branch_position3d_id],
            'pjt_points2d': [self.start_position2d_id, self._stop_position2d_id],
        }

        self.merge_packet_data(self.part.build_monitor_packet(), packet)

        return packet

    def get_object(self) -> "_splice_obj.Splice":
        if self._obj is not None:
            return self._obj()

        return self._obj

    def __release_obj_ref(self, _):
        self._obj = None

    def set_object(self, obj: "_splice_obj.Splice"):
        if obj is not None:
            self._obj = weakref.ref(obj, self.__release_obj_ref)
        else:
            self._obj = obj

    @property
    def table(self) -> PJTSplicesTable:
        return self._table

    @property
    def wires(self) -> list[list["_pjt_wire.PJTWire"], list["_pjt_wire.PJTWire"], list["_pjt_wire.PJTWire"]]:
        start_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.start_position3d_id)
        start_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.start_position3d_id)

        stop_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.stop_position3d_id)
        stop_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.stop_position3d_id)

        branch_db_ids1 = self._table.db.pjt_wires_table.select('id', stop_point3d_id=self.branch_position3d_id)
        branch_db_ids2 = self._table.db.pjt_wires_table.select('id', start_point3d_id=self.branch_position3d_id)

        def _get_wires(rows):
            ret_ = []
            for row in rows:
                ret_.append(self._table.db.pjt_wires_table[row[0]])

            return ret_

        start_wires = _get_wires(start_db_ids1)
        start_wires.extend(_get_wires(start_db_ids2))

        stop_wires = _get_wires(stop_db_ids1)
        stop_wires.extend(_get_wires(stop_db_ids2))

        branch_wires = _get_wires(branch_db_ids1)
        branch_wires.extend(_get_wires(branch_db_ids2))

        return [start_wires, stop_wires, branch_wires]

    _stored_branch_position3d: "_pjt_point3d.PJTPoint3D" = None

    @property
    def branch_position3d(self) -> "_point.Point":
        if self._stored_branch_position3d is None and self._obj is not None:

            point_id = self.branch_position3d_id
            self._stored_branch_position3d = self._table.db.pjt_points3d_table[point_id]
            self._stored_branch_position3d.add_object(self._obj())

        return self._stored_branch_position3d.point

    @property
    def branch_position3d_id(self) -> int:
        point_id = self._table.select('branch_point3d_id', id=self._db_id)[0][0]
        if point_id is None:
            self._table.execute(
                f'INSERT INTO pjt_points3d (project_id, x, y, z) VALUES (?, ?, ?, ?);',
                (self._table.project_id, 0.0, 0.0, 0.0)
                )

            self._table.commit()
            point_id = self._table.lastrowid
            self.branch_position3d_id = point_id

        return point_id

    @branch_position3d_id.setter
    def branch_position3d_id(self, value: int):
        self._table.update(self._db_id, branch_point3d_id=value)

    _stored_position2d: "_pjt_point2d.PJTPoint2D" = None

    @property
    def position2d(self) -> "_point.Point":
        if self._stored_position2d is None and self._obj is not None:

            point_id = self.position2d_id

            self._stored_position2d = self._table.db.pjt_points2d_table[point_id]
            self._stored_position2d.add_object(self._obj())
        return self._stored_position2d.point

    @property
    def position2d_id(self) -> int:
        return self._table.select('point2d_id', id=self._db_id)[0][0]

    @position2d_id.setter
    def position2d_id(self, value: int):
        self._table.update(self._db_id, point2d_id=value)
        self._process_callbacks()

    @property
    def circuit(self) -> "_pjt_circuit.PJTCircuit":
        circuit_id = self.circuit_id
        return self._table.db.pjt_circuits_table[circuit_id]

    @property
    def circuit_id(self) -> int:
        return self._table.select('circuit_id', id=self._db_id)[0][0]

    @circuit_id.setter
    def circuit_id(self, value: int):
        self._table.update(self._db_id, circuit_id=value)
        self._process_callbacks()

    @property
    def resistance(self) -> float:
        return self.part.resistance

    @property
    def part(self) -> "_splice.Splice":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.splices_table[part_id]

    @property
    def propgrid(self) -> tuple[_prop_grid.Category, _prop_grid.Category, _prop_grid.Category]:

        # TODO: Rewrite the splices so they accept models and a set number
        #  of splice points. It also needs to be written so there can be a
        #  single splice point and the number of connected wires would be
        #  dictated by the diameter of the splice

        group = _prop_grid.Category('Project')

        notes_prop = self._notes_propgrid
        name_prop = self._name_propgrid

        angle_group = _prop_grid.Property('Angle')
        angle2d_prop = self._angle2d_propgrid
        angle3d_prop = self._angle3d_propgrid
        angle2d_prop.SetLabel('2D')
        angle3d_prop.SetLabel('3D')
        angle_group.Append(angle2d_prop)
        angle_group.Append(angle3d_prop)

        circuit_prop = self._circuit_propgrid

        position_prop = self._start_stop_position3d_propgrid

        _ = self.branch_position3d
        branch_prop = self._stored_branch_position3d.propgrid
        branch_prop.SetLabel('Branch Position 3D')
        branch_prop.SetName('branch_position3d')

        visible_group = _prop_grid.Property('Visible')

        visible2d_prop = self._visible2d_propgrid
        visible3d_prop = self._visible3d_propgrid
        visible2d_prop.SetLabel('2D')
        visible3d_prop.SetLabel('3D')
        visible_group.Append(visible2d_prop)
        visible_group.Append(visible3d_prop)

        group.Append(name_prop)
        group.Append(notes_prop)
        group.Append(angle_group)
        group.Append(position_prop)
        group.Append(branch_prop)
        group.Append(visible_group)

        part_prop = self._part_propgrid

        return group, part_prop, circuit_prop
