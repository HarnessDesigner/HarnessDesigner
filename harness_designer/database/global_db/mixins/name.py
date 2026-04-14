from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class NameMixin(BaseMixin):

    @property
    def name(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @name.setter
    def name(self, value: str):
        self._table.update(self._db_id, name=value)

    @property
    def _name_propgrid(self) -> _prop_grid.Property:
        prop = _prop_grid.StringProperty('Name', 'name', self.name)

        return prop

    def get_name_control(self, parent):
        ctrl = _prop_grid.StringProperty(parent, 'Name', self.name)

        def _on_name(evt: _prop_grid.PropertyEvent):
            name = evt.GetValue()
            self.name = name

        ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, _on_name)

        return ctrl

