from typing import TYPE_CHECKING, Iterable as _Iterable

from .pjt_bases import PJTEntryBase, PJTTableBase


if TYPE_CHECKING:
    from . import pjt_concentric as _pjt_concentric
    from . import pjt_concentric_wire as _pjt_concentric_wire

    from ...objects import boot as _boot_obj


class PJTConcentricLayersTable(PJTTableBase):
    __table_name__ = 'pjt_concentric_layers'

    def __iter__(self) -> _Iterable["PJTConcentricLayer"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTConcentricLayer(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTConcentricLayer":
        if isinstance(item, int):
            if item in self:
                return PJTConcentricLayer(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, idx: int, num_wires: int, num_fillers: int,
               concentric_id: int, diameter: float) -> "PJTConcentricLayer":

        db_id = PJTTableBase.insert(self, idx=idx, num_wires=num_wires, num_fillers=num_fillers,
                                    concentric_id=concentric_id, diameter=diameter)

        return PJTConcentricLayer(self, db_id, self.project_id)


class PJTConcentricLayer(PJTEntryBase):
    _table: PJTConcentricLayersTable = None

    def get_object(self) -> "_boot_obj.Boot":
        return self._obj

    def set_object(self, obj: "_boot_obj.Boot"):
        self._obj = obj

    @property
    def table(self) -> PJTConcentricLayersTable:
        return self._table

    @property
    def wires(self) -> list["_pjt_concentric_wire.PJTConcentricWire"]:
        res = []
        db_ids = self._table.db.pjt_concentric_wires_table.select('id', layer_id=self.db_id)
        for db_id in db_ids:
            res.append(self._table.db.pjt_concentric_wires_table[db_id[0]])

        return res

    @property
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        concentric_id = self.concentric_id
        return self._table.db.pjt_concentrics_table[concentric_id]

    @property
    def concentric_id(self) -> int:
        return self._table.select('concentric_id', id=self._db_id)[0][0]

    @concentric_id.setter
    def concentric_id(self, value: int):
        self._table.update(self._db_id, concentric_id=value)
        self._process_callbacks()

    @property
    def index(self) -> int:
        return self._table.select('idx', id=self._db_id)[0][0]

    @index.setter
    def index(self, value: int):
        self._table.update(self._db_id, idx=value)
        self._process_callbacks()

    @property
    def num_wires(self) -> int:
        return self._table.select('num_wires', id=self._db_id)[0][0]

    @num_wires.setter
    def num_wires(self, value: int):
        self._table.update(self._db_id, num_wires=value)
        self._process_callbacks()

    @property
    def num_fillers(self) -> int:
        return self._table.select('num_fillers', id=self._db_id)[0][0]

    @num_fillers.setter
    def num_fillers(self, value: int):
        self._table.update(self._db_id, num_fillers=value)
        self._process_callbacks()

    @property
    def diameter(self) -> float:
        return self._table.select('diameter', id=self._db_id)[0][0]

    @diameter.setter
    def diameter(self, value: float):
        self._table.update(self._db_id, diameter=value)
        self._process_callbacks()
