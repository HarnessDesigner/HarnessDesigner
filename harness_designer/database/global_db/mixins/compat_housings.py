# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType

from ....ui import prop_ctrls as _prop_ctrls


if TYPE_CHECKING:
    from .. import housing as _housing


class CompatHousingsMixin(BaseMixin):
    """Represent a compat housings mixin in :mod:`harness_designer.database.global_db.mixins.compat_housings`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_compat_housings: list["_housing.Housing"] | DefaultStoredValueType = DefaultStoredValue

    @property
    def compat_housings(self) -> list["_housing.Housing"]:
        """Return the compat housings.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_housing.Housing']
        """
        if self._stored_compat_housings is DefaultStoredValue:
            part_numbers = [pn for pn in self.compat_housings_array if pn]

            if not part_numbers:
                self._stored_compat_housings = []
            else:
                from .. import housing as _housing_module

                housings_table = self._table.db.housings_table
                placeholders = ', '.join('?' * len(part_numbers))
                housings_table.execute(
                    f'SELECT id, part_number FROM housings WHERE part_number IN ({placeholders});',
                    part_numbers
                )
                found = {part_number: db_id for db_id, part_number in housings_table.fetchall()}

                self._stored_compat_housings = [
                    _housing_module.Housing(housings_table, found[pn])
                    for pn in part_numbers if pn in found
                ]

        return self._stored_compat_housings

    _stored_compat_housings_array: list[str] | DefaultStoredValueType = DefaultStoredValue

    @property
    def compat_housings_array(self) -> list[str]:
        """Return the compat housings array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        if self._stored_compat_housings_array is DefaultStoredValue:
            value = self._table.select('compat_housings', id=self._db_id)[0][0]

            if value.startswith('['):
                value = value[1:-1]

            self._stored_compat_housings_array = value.split(', ')

        return self._stored_compat_housings_array

    @compat_housings_array.setter
    def compat_housings_array(self, value: list[str]):
        """Set the compat housings array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        self._stored_compat_housings_array = value
        self._stored_compat_housings = DefaultStoredValue
        value = ", ".join(value)

        self._table.update(self._db_id, compat_housings=value)
        self._populate('compat_housings_array')


class CompatHousingsControl(_prop_ctrls.ArrayStringProperty):
    """Represent a compat housings control in :mod:`harness_designer.database.global_db.mixins.compat_housings`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`CompatHousingsControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: CompatHousingsMixin = None
        super().__init__(parent, 'Compatible Housings')

        self.propertyChanged.connect(self._on_compat_housings)

    def set_obj(self, db_obj: CompatHousingsMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`CompatHousingsMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue([])
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.compat_housings_array)
            self.setEnabled(True)

    def _on_compat_housings(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat housings event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_housings = evt.GetValue()
        self.db_obj.compat_housings_array = compat_housings
