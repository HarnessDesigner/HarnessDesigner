# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .bases import TableBase
from ... import utils as _utils


class SettingsTable(TableBase):
    """Represent a settings table in :mod:`harness_designer.database.global_db.setting`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'settings'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import settings

        return settings.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import settings

        settings.table.add_to_db(self)
        settings.add_records(self._con, splash, _utils.get_appdata())

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import settings

        settings.table.update_fields(self)

    def __getitem__(self, item):
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        :raises AttributeError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            value = self.select('value', id=item)
            if not value:
                raise IndexError(str(item))

            try:
                return eval(value[0][0])
            except SyntaxError:
                return value[0][0]

        value = self.select('value', name=item)

        if not value:
            raise AttributeError(item)

        try:
            return eval(value[0][0])
        except SyntaxError:
            return value[0][0]
