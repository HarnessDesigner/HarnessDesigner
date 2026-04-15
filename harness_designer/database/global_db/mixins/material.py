from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid

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


class MaterialControl(_prop_grid.ComboBoxProperty):

    def __init__(self, parent):

        self.db_obj: MaterialMixin = None
        self.choices: list[str] = []

        super().__init__(parent, 'Material', '', [])
        self.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_material)

    def set_obj(self, db_obj: MaterialMixin):
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []
            self.SetItems(self.choices)
            self.SetValue('')
            self.Enable(False)
        else:
            db_obj.table.execute('SELECT name FROM materials;')
            rows = db_obj.table.fetchall()

            self.choices = sorted([row[0] for row in rows])
            self.SetItems(self.choices)
            self.SetValue(db_obj.material.name)
            self.Enable(True)

    def _on_material(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()

        self.db_obj.table.execute('SELECT id FROM materials WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.materials_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.SetItems(self.choices)
            self.SetValue(name)

        self.db_obj.material_id = db_id

