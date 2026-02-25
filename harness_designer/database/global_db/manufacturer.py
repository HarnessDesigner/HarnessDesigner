
from typing import Iterable as _Iterable

from . import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin


class ManufacturersTable(TableBase):
    __table_name__ = 'manufacturers'

    def __iter__(self) -> _Iterable["Manufacturer"]:

        for db_id in TableBase.__iter__(self):
            yield Manufacturer(self, db_id)

    def __getitem__(self, item) -> "Manufacturer":
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

        db_id = TableBase.insert(self, name=name, description=description, address=address,
                                 contact_person=contact_person, phone=phone, ext=ext, email=email,
                                 website=website)

        return Manufacturer(self, db_id)

    @property
    def choices(self) -> list[str]:
        return [row[0] for row in self.execute(f'SELECT DISTINCT name FROM {self.__table_name__};')]


class Manufacturer(EntryBase, NameMixin, DescriptionMixin):
    _table: ManufacturersTable = None

    @property
    def address(self) -> str:
        return self._table.select('address', id=self._db_id)[0][0]

    @address.setter
    def address(self, value: str):
        self._table.update(self._db_id, address=value)

    @property
    def contact_person(self) -> str:
        return self._table.select('contact_person', id=self._db_id)[0][0]

    @contact_person.setter
    def contact_person(self, value: str):
        self._table.update(self._db_id, contact_person=value)

    @property
    def phone(self) -> str:
        return self._table.select('phone', id=self._db_id)[0][0]

    @phone.setter
    def phone(self, value: str):
        self._table.update(self._db_id, phone=value)

    @property
    def ext(self) -> str:
        return self._table.select('ext', id=self._db_id)[0][0]

    @ext.setter
    def ext(self, value: str):
        self._table.update(self._db_id, ext=value)

    @property
    def email(self) -> str:
        return self._table.select('email', id=self._db_id)[0][0]

    @email.setter
    def email(self, value: str):
        self._table.update(self._db_id, email=value)

    @property
    def website(self) -> str:
        return self._table.select('website', id=self._db_id)[0][0]

    @website.setter
    def website(self, value: str):
        self._table.update(self._db_id, website=value)
