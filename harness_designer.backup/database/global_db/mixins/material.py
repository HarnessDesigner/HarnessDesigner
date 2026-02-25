from typing import TYPE_CHECKING

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import material as _material


class MaterialMixin(BaseMixin):

    @property
    def material(self) -> "_material.Material":
        material_id = self._table.select('material_id', id=self._db_id)
        return self._table.db.materials_table[material_id[0][0]]

    @material.setter
    def material(self, value: "_material.Material"):
        self.material_id = value.db_id

    @property
    def material_id(self) -> int:
        return self._table.select('material_id', id=self._db_id)[0][0]

    @material_id.setter
    def material_id(self, value: int):
        self._table.update(self._db_id, material_id=value)
