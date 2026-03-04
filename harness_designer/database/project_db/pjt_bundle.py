from typing import TYPE_CHECKING, Iterable as _Iterable, Union

from . import PJTEntryBase, PJTTableBase
from .mixins import PartMixin, StartStopPosition3DMixin, Visible3DMixin, NameMixin


if TYPE_CHECKING:
    from . import pjt_concentric as _pjt_concentric
    from . import pjt_bundle_layout as _pjt_bundle_layout
    from . import pjt_wire as _pjt_wire

    from ..global_db import bundle_cover as _bundle_cover

    from ...objects import bundle as _bundle_obj


class PJTBundlesTable(PJTTableBase):
    __table_name__ = 'pjt_bundles'

    def __iter__(self) -> _Iterable["PJTBundle"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTBundle(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTBundle":
        if isinstance(item, int):
            if item in self:
                return PJTBundle(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, part_id: int) -> "PJTBundle":
        db_id = PJTTableBase.insert(self, part_id=part_id)

        return PJTBundle(self, db_id, self.project_id)


class PJTBundle(PJTEntryBase, PartMixin, StartStopPosition3DMixin,
                Visible3DMixin, NameMixin):
    _table: PJTBundlesTable = None

    def get_object(self) -> "_bundle_obj.Bundle":
        return self._obj

    def set_object(self, obj: "_bundle_obj.Bundle"):
        self._obj = obj

    @property
    def table(self) -> PJTBundlesTable:
        return self._table

    @property
    def wires(self) -> list["_pjt_wire.PJTWire"]:
        res = []
        for layer in self.concentric.layers:
            res.extend(layer.wires)

        return res

    @property
    def concentric(self) -> "_pjt_concentric.PJTConcentric":
        concentric_id = self.table.db.pjt_concentrics_table.select('id', bundle_id=self.db_id)[0][0]
        if concentric_id is None:
            return None

        return self.table.db.pjt_concentrics_table[concentric_id]

    @property
    def start_layout(self) -> Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.start_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    @property
    def stop_layout(self) -> Union["_pjt_bundle_layout.PJTBundleLayout", None]:
        db_ids = self._table.db.pjt_bundle_layouts_table.select('id', point3d_id=self.stop_position3d_id)
        if not db_ids:
            return None

        return self._table.db.pjt_bundle_layouts_table[db_ids[0][0]]

    @property
    def part(self) -> "_bundle_cover.BundleCover":
        part_id = self.part_id
        if part_id is None:
            return None

        return self._table.db.global_db.bundle_covers_table[part_id]
