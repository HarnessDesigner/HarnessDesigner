# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType


if TYPE_CHECKING:
    from .. import manufacturer as _manufacturer  # NOQA


class ManufacturerMixin(BaseMixin):
    """Represent a manufacturer mixin in :mod:`harness_designer.database.global_db.mixins.manufacturer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_manufacturer: "DefaultStoredValueType | _manufacturer.Manufacturer" = DefaultStoredValue

    @property
    def manufacturer(self) -> "_manufacturer.Manufacturer":
        """Return the manufacturer.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_manufacturer.Manufacturer`
        """
        if self._stored_manufacturer is DefaultStoredValue:
            from .. import manufacturer as _manufacturer  # NOQA

            mfg_id = self._table.select('mfg_id', id=self._db_id)
            self._stored_manufacturer = _manufacturer.Manufacturer(
                self._table.db.manufacturers_table, mfg_id[0][0])

        return self._stored_manufacturer

    _stored_mfg_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def mfg_id(self) -> int:
        """Return the mfg ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_mfg_id is DefaultStoredValue:
            self._stored_mfg_id = self._table.select('mfg_id', id=self._db_id)[0][0]

        return self._stored_mfg_id

    @mfg_id.setter
    def mfg_id(self, value: int):
        """Set the mfg ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_mfg_id = value
        self._stored_manufacturer = DefaultStoredValue

        self._table.update(self._db_id, mfg_id=value)
        self._populate('mfg_id')


class ManufacturerControl(_prop_ctrls.Category):
    """Represent a manufacturer control in :mod:`harness_designer.database.global_db.mixins.manufacturer`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """
    
    def __init__(self, parent):
        """Initialise the :class:`ManufacturerControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: ManufacturerMixin = None
        self.choices: list[str] = []
        
        super().__init__(parent, 'Manufacturer')

        self.name_ctrl = _prop_ctrls.ComboBoxProperty(self, 'Name')
        self.desc_ctrl = _prop_ctrls.LongStringProperty(self, 'Description')
        self.address_ctrl = _prop_ctrls.LongStringProperty(self, 'Address')
        self.contact_ctrl = _prop_ctrls.StringProperty(self, 'Contact')
        self.phone_ctrl = _prop_ctrls.StringProperty(self, 'Phone')
        self.ext_ctrl = _prop_ctrls.StringProperty(self, 'Ext')
        self.email_ctrl = _prop_ctrls.StringProperty(self, 'Email')
        self.website_ctrl = _prop_ctrls.StringProperty(self, 'Website')

        self.addWidget(self.name_ctrl)
        self.addWidget(self.desc_ctrl)
        self.addWidget(self.address_ctrl)
        self.addWidget(self.contact_ctrl)
        self.addWidget(self.phone_ctrl)
        self.addWidget(self.ext_ctrl)
        self.addWidget(self.email_ctrl)
        self.addWidget(self.website_ctrl)

        self.website_ctrl.propertyChanged.connect(self._on_website_change)
        self.email_ctrl.propertyChanged.connect(self._on_email_change)
        self.ext_ctrl.propertyChanged.connect(self._on_ext_change)
        self.phone_ctrl.propertyChanged.connect(self._on_phone_change)
        self.contact_ctrl.propertyChanged.connect(self._on_contact_change)
        self.address_ctrl.propertyChanged.connect(self._on_addr_change)
        self.desc_ctrl.propertyChanged.connect(self._on_desc_change)
        self.name_ctrl.propertyChanged.connect(self._on_name_change)

    def set_obj(self, db_obj: ManufacturerMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`ManufacturerMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.name_ctrl.SetItems(self.choices)
            self.name_ctrl.SetValue('')

            self.desc_ctrl.SetValue('')
            self.address_ctrl.SetValue('')
            self.contact_ctrl.SetValue('')
            self.phone_ctrl.SetValue('')
            self.ext_ctrl.SetValue('')
            self.email_ctrl.SetValue('')
            self.website_ctrl.SetValue('')

            self.name_ctrl.setEnabled(False)
            self.desc_ctrl.setEnabled(False)
            self.address_ctrl.setEnabled(False)
            self.contact_ctrl.setEnabled(False)
            self.phone_ctrl.setEnabled(False)
            self.ext_ctrl.setEnabled(False)
            self.email_ctrl.setEnabled(False)
            self.website_ctrl.setEnabled(False)

        else:
            mfg = db_obj.manufacturer

            self.db_obj.table.execute(f'SELECT name, description, address, contact_person, phone, ext, email, website FROM manufacturers WHERE id={mfg.db_id};')
            rows = db_obj.table.fetchall()
            name, desc, addr, contact, phone, ext, email, website = rows[0]

            db_obj.table.execute(f'SELECT name FROM manufacturers;')
            rows = db_obj.table.fetchall()

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

            self.name_ctrl.setEnabled(True)
            self.desc_ctrl.setEnabled(True)
            self.address_ctrl.setEnabled(True)
            self.contact_ctrl.setEnabled(True)
            self.phone_ctrl.setEnabled(True)
            self.ext_ctrl.setEnabled(True)
            self.email_ctrl.setEnabled(True)
            self.website_ctrl.setEnabled(True)

    def _on_name_change(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the name change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()
        rows = self.db_obj.table.execute(f'SELECT id, description, address, contact_person, phone, ext, email, website FROM manufacturers WHERE name="{name}";')
        if rows:
            db_id, desc, addr, contact, phone, ext, email, website = rows[0]
            self.db_obj.mfg_id = db_id
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
        """Handle the desc change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.manufacturer.description = evt.GetValue()

    def _on_addr_change(self, evt):
        """Handle the addr change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.manufacturer.address = evt.GetValue()

    def _on_contact_change(self, evt):
        """Handle the contact change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.manufacturer.contact_person = evt.GetValue()

    def _on_phone_change(self, evt):
        """Handle the phone change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.manufacturer.phone = evt.GetValue()

    def _on_ext_change(self, evt):
        """Handle the ext change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.manufacturer.ext = evt.GetValue()

    def _on_email_change(self, evt):
        """Handle the email change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.manufacturer.email = evt.GetValue()

    def _on_website_change(self, evt):
        """Handle the website change event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: UNKNOWN
        """
        self.db_obj.manufacturer.website = evt.GetValue()
