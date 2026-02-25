
from typing import TYPE_CHECKING, Iterable as _Iterable

from . import PJTEntryBase, PJTTableBase

if TYPE_CHECKING:
    from . import pjt_transition_branch as _pjt_transition_branches
    from . import pjt_concentric_layer as _pjt_concentric_layer

    from . import pjt_bundle as _pjt_bundle


class PJTConcentricsTable(PJTTableBase):
    __table_name__ = 'pjt_concentrics'

    def __iter__(self) -> _Iterable["PJTConcentric"]:
        for db_id in PJTTableBase.__iter__(self):
            yield PJTConcentric(self, db_id, self.project_id)

    def __getitem__(self, item) -> "PJTConcentric":
        if isinstance(item, int):
            if item in self:
                return PJTConcentric(self, item, self.project_id)
            raise IndexError(str(item))

        raise KeyError(item)

    def insert(self, bundle_id: int | None, transition_branch_id: int | None) -> "PJTConcentric":

        db_id = PJTTableBase.insert(self, bundle_id=bundle_id, transition_branch_id=transition_branch_id)

        return PJTConcentric(self, db_id, self.project_id)


class PJTConcentric(PJTEntryBase):
    _table: PJTConcentricsTable = None

    @property
    def layers(self) -> list["_pjt_concentric_layer.PJTConcentricLayer"]:
        layers = []

        db_ids = self.table.db.pjt_concentric_layers_table.select("id", concentric_id=self.db_id)
        for db_id in db_ids:
            layers.append(self.table.db.pjt_concentric_layers_table[db_id[0]])

        return sorted(layers, key=lambda x: x.index)

    @property
    def table(self) -> PJTConcentricsTable:
        return self._table

    @property
    def bundle(self) -> "_pjt_bundle.PJTBundle":
        bundle_id = self.bundle_id
        if bundle_id is None:
            return None

        return self._table.db.pjt_bundles_table[bundle_id]

    @property
    def bundle_id(self) -> int:
        return self._table.select('bundle_id', id=self._db_id)[0][0]

    @bundle_id.setter
    def bundle_id(self, value: int):
        self._table.update(self._db_id, bundle_id=value)
        self._process_callbacks()

    @property
    def transition_branch(self) -> "_pjt_transition_branches.PJTTransitionBranch":
        transition_branch_id = self.transition_branch_id
        if transition_branch_id is None:
            return None

        return self._table.db.pjt_transition_branches_table[transition_branch_id]

    @property
    def transition_branch_id(self) -> int:
        return self._table.select('transition_branch_id', id=self._db_id)[0][0]

    @transition_branch_id.setter
    def transition_branch_id(self, value: int):
        self._table.update(self._db_id, transition_branch_id=value)
        self._process_callbacks()
