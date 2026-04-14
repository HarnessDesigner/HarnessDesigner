from typing import TYPE_CHECKING

from ....ui.editor_obj import prop_grid as _prop_grid

from .base import BaseMixin


if TYPE_CHECKING:
    from .. import manufacturer as _manufacturer  # NOQA


class ManufacturerMixin(BaseMixin):

    @property
    def manufacturer(self) -> "_manufacturer.Manufacturer":
        from .. import manufacturer as _manufacturer  # NOQA

        mfg_id = self._table.select('mfg_id', id=self._db_id)
        return _manufacturer.Manufacturer(self._table.db.manufacturers_table, mfg_id[0][0])

    @manufacturer.setter
    def manufacturer(self, value: "_manufacturer.Manufacturer"):
        self._table.update(self._db_id, mfg_id=value.db_id)

    @property
    def mfg_id(self) -> int:
        return self._table.select('mfg_id', id=self._db_id)[0][0]

    @mfg_id.setter
    def mfg_id(self, value: int):
        self._table.update(self._db_id, mfg_id=value)


class ManufacturerControl(_prop_grid.Category):
    
    def __init__(self, parent):
        self.db_obj: ManufacturerMixin = None
        self.choices: list[str] = []
        
        super().__init__(parent, 'Manufacturer')

        self.name_ctrl = _prop_grid.ComboBoxProperty(self, 'Name', '', [])
        self.desc_ctrl = _prop_grid.LongStringProperty(self, 'Description', '')
        self.address_ctrl = _prop_grid.LongStringProperty(self, 'Address', '')
        self.contact_ctrl = _prop_grid.StringProperty(self, 'Contact', '')
        self.phone_ctrl = _prop_grid.StringProperty(self, 'Phone', '')
        self.ext_ctrl = _prop_grid.StringProperty(self, 'Ext', '')
        self.email_ctrl = _prop_grid.StringProperty(self, 'Email', '')
        self.website_ctrl = _prop_grid.StringProperty(self, 'Website', '')

        self.website_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_website_change)
        self.email_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_email_change)
        self.ext_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_ext_change)
        self.phone_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_phone_change)
        self.contact_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_contact_change)
        self.address_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_addr_change)
        self.desc_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_desc_change)
        self.name_ctrl.Bind(_prop_grid.EVT_PROPERTY_CHANGED, self._on_name_change)

    def set_obj(self, db_obj: ManufacturerMixin):
        self.db_obj = db_obj

        mfg = self.db_obj.manufacturer

        self.db_obj.table.execute(f'SELECT name, description, address, contact_person, phone, ext, email, website FROM manufacturers WHERE id={mfg.db_id};')
        rows = self.db_obj.table.fetchall()
        name, desc, addr, contact, phone, ext, email, website = rows[0]

        self.db_obj.table.execute(f'SELECT name FROM manufacturers;')
        rows = self.db_obj.table.fetchall()

        self.choices = sorted([row[0] for row in rows])

        self.name_ctrl.SetItems(self.choices)
        self.name_ctrl.SetValue(name)

        self.desc_ctrl.SetValue(desc)
        self.address_ctrl.SetValue(addr)
        self.contact_ctrl.SetValue(contact)
        self.phone_ctrl.SetValue(phone)
        self.ext_ctrl.SetValue(ext)
        self.email_ctrl.SetValue(email)
        self.website_ctrl.SetValue(website)

    def _on_name_change(self, evt: _prop_grid.PropertyEvent):
        name = evt.GetValue()
        rows = self.db_obj.table.execute(f'SELECT id, description, address, contact_person, phone, ext, email, website FROM manufacturers WHERE name="{name}";')
        if rows:
            id, desc, addr, contact, phone, ext, email, website = rows[0]
            self.db_obj.mfg_id = id
        else:
            mfg = self.db_obj.table.db.manufacturers_table.insert(name, '', '', '', '', '', '', '')
            self.db_obj.mfg_id = mfg.db_id

            desc = ''
            addr = ''
            contact = ''
            phone = ''
            ext = ''
            email = ''
            website = ''

            self.choices.append(name)
            self.choices.sort()

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue(name)

        self.desc_ctrl.SetValue(desc)
        self.address_ctrl.SetValue(addr)
        self.contact_ctrl.SetValue(contact)
        self.phone_ctrl.SetValue(phone)
        self.ext_ctrl.SetValue(ext)
        self.email_ctrl.SetValue(email)
        self.website_ctrl.SetValue(website)

    def _on_desc_change(self, evt):
        self.db_obj.manufacturer.description = evt.GetValue()

    def _on_addr_change(self, evt):
        self.db_obj.manufacturer.address = evt.GetValue()

    def _on_contact_change(self, evt):
        self.db_obj.manufacturer.contact_person = evt.GetValue()

    def _on_phone_change(self, evt):
        self.db_obj.manufacturer.phone = evt.GetValue()

    def _on_ext_change(self, evt):
        self.db_obj.manufacturer.ext = evt.GetValue()

    def _on_email_change(self, evt):
        self.db_obj.manufacturer.email = evt.GetValue()

    def _on_website_change(self, evt):
        self.db_obj.manufacturer.website = evt.GetValue()
