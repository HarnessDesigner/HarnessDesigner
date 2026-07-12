# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType

if TYPE_CHECKING:
    from .. import protection as _protection


class ProtectionMixin(BaseMixin):
    """Represent a protection mixin in :mod:`harness_designer.database.global_db.mixins.protection`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_protection_id: int | DefaultStoredValueType = DefaultStoredValue

    @property
    def protection_id(self) -> int:
        """Return the protection ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        if self._stored_protection_id is DefaultStoredValue:
            self._stored_protection_id = self._table.select('protection_id', id=self._db_id)[0][0]

        return self._stored_protection_id

    @protection_id.setter
    def protection_id(self, value: int):
        """Set the protection ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._stored_protection_id = value
        self._stored_protections = DefaultStoredValue
        self._table.update(self._db_id, protection_id=value)
        self._populate('protection_id')

    _stored_protections: "DefaultStoredValueType | _protection.Protection" = DefaultStoredValue

    @property
    def protections(self) -> "_protection.Protection":
        """Return the protections.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_protection.Protection`
        """
        if self._stored_protections is DefaultStoredValue:
            self._stored_protections = self.table.db.protections_table[self.protection_id]

        return self._stored_protections


class ProtectionControl(_prop_ctrls.AutocompleteStringProperty):
    """Represent a protection control in :mod:`harness_designer.database.global_db.mixins.protection`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`ProtectionControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: ProtectionMixin = None
        self.choices: list[str] = []

        super().__init__(parent, 'Protections')

        self.propertyChanged.connect(self._on_protection)

    def set_obj(self, db_obj: ProtectionMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`ProtectionMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.SetItems(self.choices)
            self.SetValue('')

            self.setEnabled(False)
        else:
            db_obj.table.execute('SELECT name FROM protections;')
            rows = db_obj.table.fetchall()

            self.choices = [row[0] for row in rows]

            self.SetItems(self.choices)
            self.SetValue(db_obj.protections.name)

            self.setEnabled(True)

    def _on_protection(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the protection event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        protection = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM protections WHERE name="{protection}";')
        rows = self.db_obj.table.fetchall()
        if rows:
            db_id = rows[0][0]
        else:
            db_obj = self.db_obj.table.db.protections_table.insert(protection)
            db_id = db_obj.db_id

            self.choices.append(protection)
            self.SetItems(self.choices)
            self.SetValue(protection)

        self.db_obj.protection_id = db_id
