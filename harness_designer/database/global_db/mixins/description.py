from .base import BaseMixin

from ....ui.editor_obj import prop_grid as _prop_grid


class DescriptionMixin(BaseMixin):

    @property
    def description(self) -> str:
        return self._table.select('description', id=self._db_id)[0][0]

    @description.setter
    def description(self, value: str):
        self._table.update(self._db_id, description=value)

    @property
    def _description_propgrid(self) -> _prop_grid.Property:

        desc_prop = _prop_grid.LongStringProperty('Description', 'description', self.description)

        return desc_prop
