# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from ..bases import EntryBase, TableBase
from ..mixins import (NameMixin, DescriptionMixin)

from .... import image as _image


class IPFluidsTable(TableBase):
    """Represent an ip fluids table in :mod:`harness_designer.database.global_db.ip.fluid`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'ip_fluids'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ...create_database import ip_fluids

        return ip_fluids.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ...create_database import ip_fluids

        ip_fluids.table.add_to_db(self)
        ip_fluids.add_records(self._con, splash)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ...create_database import ip_fluids

        ip_fluids.table.update_fields(self)

    def __getitem__(self, item) -> "IPFluid":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`IPFluid`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return IPFluid(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return IPFluid(self, db_id[0][0])

        raise KeyError(item)

    def __iter__(self) -> _Iterable["IPFluid"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['IPFluid']
        """
        for db_id in TableBase.__iter__(self):
            yield IPFluid(self, db_id)

    def insert(self, name: str, short_desc: str, description: str, icon_data: bytes | None) -> "IPFluid":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param short_desc: Value for ``short_desc``.
        :type short_desc: str
        :param description: Value for ``description``.
        :type description: str
        :param icon_data: Value for ``icon_data``.
        :type icon_data: bytes | None
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`IPFluid`
        """
        db_id = TableBase.insert(self, name=name, short_desc=short_desc, description=description, icon_data=icon_data)
        return IPFluid(self, db_id)


class IPFluid(EntryBase, NameMixin, DescriptionMixin):
    """Represent an ip fluid in :mod:`harness_designer.database.global_db.ip.fluid`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: IPFluidsTable = None

    @property
    def short_desc(self) -> str:
        """Return the short desc.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('short_desc', id=self._db_id)[0][0]

    @short_desc.setter
    def short_desc(self, value: str):
        """Set the short desc.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, short_desc=value)

    @property
    def icon(self) -> _image.Image:
        """Return the icon.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_image.Image`
        """
        return getattr(_image.ip, f'IPX{self.name}')
