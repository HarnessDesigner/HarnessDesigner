from typing import TYPE_CHECKING

from .base import BaseMixin

if TYPE_CHECKING:
    from .. import model3d as _model3d


class Model3DMixin(BaseMixin):

    @property
    def model3d(self) -> "_model3d.Model3D":
        model3d_id = self.model3d_id
        if model3d_id is None:
            return None

        return self._table.db.models3d_table[model3d_id]

    @model3d.setter
    def model3d(self, value: "_model3d.Model3D"):
        self._table.update(self._db_id, model3d_id=value.db_id)

    @property
    def model3d_id(self) -> int:
        return self._table.select('model3d_id', id=self._db_id)[0][0]

    @model3d_id.setter
    def model3d_id(self, value: int):
        self._table.update(self._db_id, model3d_id=value)
