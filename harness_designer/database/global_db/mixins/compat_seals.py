# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from .base import BaseMixin

from ....ui import prop_ctrls as _prop_ctrls


if TYPE_CHECKING:
    from .. import seal as _seal


class CompatSealsMixin(BaseMixin):
    """Represent a compat seals mixin in :mod:`harness_designer.database.global_db.mixins.compat_seals`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def compat_seals(self) -> list["_seal.Seal"]:
        """Return the compat seals.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list['_seal.Seal']
        """
        compat_seals = self.compat_seals_array
        res = []
        for part_number in compat_seals:
            try:
                res.append(self._table.db.seals_table[part_number])
            except KeyError:
                pass
        return res

    @property
    def compat_seals_array(self) -> list[str]:
        """Return the compat seals array.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: list[str]
        """
        value = self._table.select('compat_seals', id=self._db_id)[0][0]
        return value[1:-1].split(', ')

    @compat_seals_array.setter
    def compat_seals_array(self, value: list[str]):
        """Set the compat seals array.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: list[str]
        """
        value = f'[{", ".join(value)}]'
        self._table.update(self._db_id, compat_seals=value)
        self._populate('compat_seals_array')


class CompatSealsControl(_prop_ctrls.ArrayStringProperty):
    """Represent a compat seals control in :mod:`harness_designer.database.global_db.mixins.compat_seals`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`CompatSealsControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: CompatSealsMixin = None
        super().__init__(parent, 'Compatible Seals')

        self.propertyChanged.connect(self._on_compat_housings)

    def set_obj(self, db_obj: CompatSealsMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`CompatSealsMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue([])
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.compat_seals_array)
            self.setEnabled(True)

    def _on_compat_housings(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the compat housings event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        compat_seals = evt.GetValue()
        self.db_obj.compat_seals_array = compat_seals
