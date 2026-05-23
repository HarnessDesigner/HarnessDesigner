# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin

from ....ui import prop_ctrls as _prop_ctrls


if TYPE_CHECKING:
    from .. import housing as _housing


class CompatHousingsMixin(BaseMixin):
    """Represent a compat housings mixin in :mod:`harness_designer.database.global_db.mixins.compat_housings`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def compat_housings(self) -> list["_housing.Housing"]:
        """Return the compat housings.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_housing.Housing']
        """
        housings = self.compat_housings_array
        res = []
        for part_number in housings:
            try:
                res.append(self._table.db.housings_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_housings_array(self) -> list[str]:
        """Return the compat housings array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        value = self._table.select('compat_housings', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_housings_array.setter
    def compat_housings_array(self, value: list[str]):
        """Set the compat housings array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        value = f'[{", ".join(value)}]'
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

        self.property_changed.connect(self._on_compat_housings)

    def set_obj(self, db_obj: CompatHousingsMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`CompatHousingsMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue([])
            self.Enable(False)
        else:
            self.SetValue(db_obj.compat_housings_array)
            self.Enable(True)

    def _on_compat_housings(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat housings event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_housings = evt.GetValue()
        self.db_obj.compat_seals_array = compat_housings
