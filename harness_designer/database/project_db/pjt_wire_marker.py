from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase
from .mixins import Position2DMixin, Position3DMixin, PartMixin, Visible3DMixin, Visible2DMixin, NameMixin


if TYPE_CHECKING:
    from ..global_db import wire_marker as _wire_marker
    from . import pjt_wire as _pjt_wire

    from ...objects import wire_marker as _wire_marker_obj


class PJTWireMarkersTable(PJTTableBase):
    __table_name__ = 'pjt_wire_markers'

    def __iter__(self) -> _Iterable["PJTWireMarker"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTWireMarker(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTWireMarker":
        if isinstance(item, int):
            if item in self:
                return PJTWireMarker(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, point2d_id: int, point3d_id: int,
               wire_id: int, part_id: int, label: str) -> "PJTWireMarker":

        db_id = PJTTableBase.insert(self, point2d_id=point2d_id, point3d_id=point3d_id,
                                    wire_id=wire_id, part_id=part_id, label=label)

        return PJTWireMarker(self, db_id, self.project_id)


class PJTWireMarker(PJTEntryBase, Position2DMixin, Position3DMixin, PartMixin,
                    Visible3DMixin, Visible2DMixin, NameMixin):
    _table: PJTWireMarkersTable = None

    def get_object(self) -> "_wire_marker_obj.WireMarker":
        return self._obj

    def set_object(self, obj: "_wire_marker_obj.WireMarker"):
        self._obj = obj

    @property
    def table(self) -> PJTWireMarkersTable:
        return self._table

    @property
    def wire(self) -> "_pjt_wire.PJTWire":
        wire_id = self.wire_id
        return self._table.db.pjt_wires_table[wire_id]

    @property
    def wire_id(self) -> int:
        return self._table.select('wire_id', id=self._db_id)[0][0]

    @wire_id.setter
    def wire_id(self, value: int):
        self._table.update(self._db_id, wire_id=value)
        self._process_callbacks()

    @property
    def part(self) -> "_wire_marker.WireMarker":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.wire_markers_table[part_id]

    @property
    def label(self) -> str:
        return self._table.select('label', id=self._db_id)[0][0]

    @label.setter
    def label(self, value: str):
        self._table.update(self._db_id, label=value)
        self._process_callbacks()
