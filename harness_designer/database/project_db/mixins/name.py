from .base import BaseMixin

from wx import propgrid as wxpg


class NameMixin(BaseMixin):

    @property
    def name(self) -> str:
        return self._table.select('name', id=self._db_id)[0][0]

    @name.setter
    def name(self, value: str):
        self._table.update(self._db_id, name=value)

    @property
    def _name_propgrid(self) -> wxpg.PGProperty:
        name_prop = wxpg.StringProperty('Name', 'name', self.name)

        return name_prop