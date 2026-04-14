
from typing import Iterable as _Iterable

from ...ui.editor_obj import prop_grid as _prop_grid

from .bases import EntryBase, TableBase
from .mixins import NameMixin, DescriptionMixin


class ManufacturersTable(TableBase):
    __table_name__ = 'manufacturers'

    def _table_needs_update(self) -> bool:
        from ..create_database import manufacturers

        return manufacturers.table.is_ok(self)

    def _add_table_to_db(self, splash):
        from ..create_database import manufacturers

        manufacturers.table.add_to_db(self)
        data_path = self._con.db_data.open(splash)
        manufacturers.add_records(self._con, splash, data_path)

    def _update_table_in_db(self):
        from ..create_database import manufacturers

        manufacturers.table.update_fields(self)

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

    def build_monitor_packet(self):

        packet = {
            'manufacturers': [self.db_id]
        }

        return packet

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

    @property
    def propgrid(self) -> _prop_grid.Property:
        group_prop = _prop_grid.Property('Manufacturer', 'manufacturer')

        rows = self.table.select('name', 'description', 'address', 'contact_person', 'phone', 'ext', 'email', 'website')

        choices = [item[0] for item in rows]

        name_prop = _prop_grid.ComboBoxProperty('Name', 'name', self.name, choices)

        def _on_name_change(evt: _prop_grid.PropertyEvent):
            name = evt.GetValue()
            rows = self.table.select('id', 'description', 'address', 'contact_person', 'phone', 'ext', 'email', 'website', name=name)
            if rows:
                id, desc, addr, contact, phone, ext, email, website = rows[0]
                desc_prop.SetValue(desc)
                address_prop.SetValue(addr)
                contact_prop.SetValue(contact)
                phone_prop.SetValue(phone)
                ext_prop.SetValue(ext)
                email_prop.SetValue(email)
                website_prop.SetValue(website)

        name_prop.Bind(_prop_grid.EVT_PROPERTY_CHANGED, _on_name_change)

        desc_prop = _prop_grid.LongStringProperty('Description', 'description', self.description)
        address_prop = _prop_grid.LongStringProperty('Address', 'address', self.address)
        contact_prop = _prop_grid.StringProperty('Contact', 'contact_person', self.contact_person)
        phone_prop = _prop_grid.StringProperty('Phon', 'phone', self.phone)
        ext_prop = _prop_grid.StringProperty('Ext', 'ext', self.ext)
        email_prop = _prop_grid.StringProperty('Email', 'email', self.email)
        website_prop = _prop_grid.StringProperty('Website', 'website', self.website)

        group_prop.Append(name_prop)
        group_prop.Append(desc_prop)
        group_prop.Append(address_prop)
        group_prop.Append(contact_prop)
        group_prop.Append(phone_prop)
        group_prop.Append(ext_prop)
        group_prop.Append(email_prop)
        group_prop.Append(website_prop)

        return group_prop
