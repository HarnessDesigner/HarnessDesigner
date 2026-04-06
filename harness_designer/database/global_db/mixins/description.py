from .base import BaseMixin

from wx import propgrid as wxpg


class DescriptionMixin(BaseMixin):

    @property
    def description(self) -> str:
        return self._table.select('description', id=self._db_id)[0][0]

    @description.setter
    def description(self, value: str):
        self._table.update(self._db_id, description=value)

    @property
    def _description_propgrid(self) -> wxpg.PGProperty:
        from ....ui.editor_obj.prop_grid import long_string_prop as _long_string_prop

        desc_prop = _long_string_prop.LongStringProperty('Description', 'description', self.description)

        return desc_prop
