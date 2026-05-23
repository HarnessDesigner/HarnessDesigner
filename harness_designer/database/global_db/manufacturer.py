# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import Iterable as _Iterable

from .bases import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin


class ManufacturersTable(TableBase):
    """Represent a manufacturers table in :mod:`harness_designer.database.global_db.manufacturer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    __table_name__ = 'manufacturers'

    def _table_needs_update(self) -> bool:
        """Execute the table needs update operation.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: bool
        """
        from ..create_database import manufacturers

        return manufacturers.table.is_ok(self)

    def _add_table_to_db(self, splash):
        """Add a table to database.

        UNKNOWN details are inferred from the callable name and signature.

        :param splash: Value for ``splash``.
        :type splash: UNKNOWN
        """
        from ..create_database import manufacturers

        manufacturers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        manufacturers.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        """Update the table in database.

        UNKNOWN details are inferred from the callable name and signature.
        """
        from ..create_database import manufacturers

        manufacturers.table.update_fields(self)

    def __iter__(self) -> _Iterable["Manufacturer"]:
        """Iterate over the available items.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Iterator or iterable result. UNKNOWN details.
        :rtype: _Iterable['Manufacturer']
        """

        for db_id in TableBase.__iter__(self):
            yield Manufacturer(self, db_id)

    def __getitem__(self, item) -> "Manufacturer":
        """Return the requested item.

        UNKNOWN details are inferred from the callable name and signature.

        :param item: Item identifier or value.
        :type item: UNKNOWN
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Manufacturer`
        :raises KeyError: Raised when the operation cannot be completed.
        :raises IndexError: Raised when the operation cannot be completed.
        """
        if isinstance(item, int):
            if item in self:
                return Manufacturer(self, item)
            raise IndexError(str(item))

        db_id = self.select('id', name=item)
        if db_id:
            return Manufacturer(self, db_id[0][0])

        raise KeyError(item)

    def insert(self, name: str, description: str, address: str, contact_person: str,
               phone: str, ext: str, email: str, website: str) -> "Manufacturer":
        """Execute the insert operation.

        UNKNOWN details are inferred from the callable name and signature.

        :param name: Name value.
        :type name: str
        :param description: Value for ``description``.
        :type description: str
        :param address: Value for ``address``.
        :type address: str
        :param contact_person: Value for ``contact_person``.
        :type contact_person: str
        :param phone: Value for ``phone``.
        :type phone: str
        :param ext: Value for ``ext``.
        :type ext: str
        :param email: Value for ``email``.
        :type email: str
        :param website: Value for ``website``.
        :type website: str
        :returns: Return value. UNKNOWN details.
        :rtype: :class:`Manufacturer`
        """

        db_id = TableBase.insert(self, name=name, description=description, address=address,
                                 contact_person=contact_person, phone=phone, ext=ext, email=email,
                                 website=website)

        return Manufacturer(self, db_id)

    @property
    def choices(self) -> list[str]:
        """Return the choices.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Manufacturer(EntryBase, NameMixin, DescriptionMixin):
    """Represent a manufacturer in :mod:`harness_designer.database.global_db.manufacturer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    _table: ManufacturersTable = None

    def build_monitor_packet(self):
        """Build the monitor packet.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Return value. UNKNOWN details.
        :rtype: UNKNOWN
        """

        packet = {
            'manufacturers': [self.db_id]
        }

        return packet

    @property
    def address(self) -> str:
        """Return the address.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('address', id=self._db_id)[0][0]

    @address.setter
    def address(self, value: str):
        """Set the address.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, address=value)
        self._populate('address')

    @property
    def contact_person(self) -> str:
        """Return the contact person.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('contact_person', id=self._db_id)[0][0]

    @contact_person.setter
    def contact_person(self, value: str):
        """Set the contact person.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, contact_person=value)
        self._populate('contact_person')

    @property
    def phone(self) -> str:
        """Return the phone.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('phone', id=self._db_id)[0][0]

    @phone.setter
    def phone(self, value: str):
        """Set the phone.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, phone=value)
        self._populate('phone')

    @property
    def ext(self) -> str:
        """Return the ext.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('ext', id=self._db_id)[0][0]

    @ext.setter
    def ext(self, value: str):
        """Set the ext.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, ext=value)
        self._populate('ext')

    @property
    def email(self) -> str:
        """Return the email.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('email', id=self._db_id)[0][0]

    @email.setter
    def email(self, value: str):
        """Set the email.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, email=value)
        self._populate('email')

    @property
    def website(self) -> str:
        """Return the website.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        return self._table.select('website', id=self._db_id)[0][0]

    @website.setter
    def website(self, value: str):
        """Set the website.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._table.update(self._db_id, website=value)
        self._populate('website')
