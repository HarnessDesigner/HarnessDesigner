
from .bases import TableBase
from ... import utils as _utils


class SettingsTable(TableBase):
    __table_name__ = 'settings'

    def _table_needs_update(self) -> bool:
        from ..create_database import settings

        return settings.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import settings

        settings.table.add_to_db(self)
        settings.add_records(self._con, splash, _utils.get_appdata())

    def _update_table_in_db(self):
        from ..create_database import settings

        settings.table.update_fields(self)

    def __getitem__(self, item):
        if isinstance(item, int):
            value = self.select('value', id=item)
            if not value:
                raise IndexError(str(item))

            return eval(value[0][0])

        value = self.select('value', name=item)

        if not value:
            raise AttributeError(item)

        return eval(value[0][0])
