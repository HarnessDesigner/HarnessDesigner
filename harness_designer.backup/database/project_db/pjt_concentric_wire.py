
from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase

if TYPE_CHECKING:
    from . import pjt_point2d as _pjt_point2d
    from . import pjt_wire as _pjt_wire
    from . import pjt_concentric_layer as _pjt_concentric_layer


class PJTConcentricWiresTable(PJTTableBase):
    __table_name__ = 'pjt_concentric_wires'

    def __iter__(self) -> _Iterable["PJTConcentricWire"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTConcentricWire(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTConcentricWire":
        if isinstance(item, int):
            if item in self:
                return PJTConcentricWire(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, layer_id: int, idx: int, wire_id: int, is_filler: bool) -> "PJTConcentricWire":
        db_id = PJTTableBase.insert(self, layer_id=layer_id, idx=idx,
                                    wire_id=wire_id, is_filler=int(is_filler))

        return PJTConcentricWire(self, db_id, self.project_id)


class PJTConcentricWire(PJTEntryBase):
    _table: PJTConcentricWiresTable = None

    @property
    def table(self) -> PJTConcentricWiresTable:
        return self._table

    @property
    def layer(self) -> "_pjt_concentric_layer.PJTConcentricLayer":
        layer_id = self.layer_id
        return self._table.db.pjt_concentric_layers_table[layer_id]

    @property
    def layer_id(self) -> int:
        return self._table.select('layer_id', id=self._db_id)[0][0]

    @layer_id.setter
    def layer_id(self, value: int):
        self._table.update(self._db_id, layer_id=value)
        self._process_callbacks()

    @property
    def index(self) -> int:
        return self._table.select('idx', id=self._db_id)[0][0]

    @index.setter
    def index(self, value: int):
        self._table.update(self._db_id, idx=value)
        self._process_callbacks()

    @property
    def is_filler(self) -> bool:
        return bool(self._table.select('is_filler', id=self._db_id)[0][0])

    @is_filler.setter
    def is_filler(self, value: bool):
        self._table.update(self._db_id, is_filler=int(value))
        self._process_callbacks()

    def wire(self) -> "_pjt_wire.PJTWire":
        wire_id = self.wire_id
        return self.table.db.pjt_wires_table[wire_id]

    @property
    def wire_id(self) -> int:
        return self._table.select('wire_id', id=self._db_id)[0][0]

    @wire_id.setter
    def wire_id(self, value: int):
        self._table.update(self._db_id, wire_id=value)
        self._process_callbacks()

    def point(self) -> "_pjt_point2d.PJTPoint2D":
        point_id = self.point_id
        return self.table.db.pjt_points2d_table[point_id]

    @property
    def point_id(self) -> int:
        return self._table.select('point_id', id=self._db_id)[0][0]

    @point_id.setter
    def point_id(self, value: int):
        self._table.update(self._db_id, point_id=value)
        self._process_callbacks()
