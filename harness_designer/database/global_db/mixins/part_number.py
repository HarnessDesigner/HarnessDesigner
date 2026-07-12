# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType

from ....ui import prop_ctrls as _prop_ctrls


class PartNumberMixin(BaseMixin):
    """Represent a part number mixin in :mod:`harness_designer.database.global_db.mixins.part_number`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_part_number: DefaultStoredValueType | str = DefaultStoredValue

    @property
    def part_number(self) -> str:
        """Return the part number.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: str
        """
        if self._stored_part_number is DefaultStoredValue:
            self._stored_part_number = self._table.select('part_number', id=self._db_id)[0][0]

        return self._stored_part_number

    @part_number.setter
    def part_number(self, value: str):
        """Set the part number.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: str
        """
        self._stored_part_number = value
        self._table.update(self._db_id, part_number=value)
        self._populate('part_number')


class PartNumberControl(_prop_ctrls.StringProperty):
    """Represent a part number control in :mod:`harness_designer.database.global_db.mixins.part_number`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`PartNumberControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: PartNumberMixin = None

        super().__init__(parent, 'Part Number')

        self.propertyChanged.connect(self._on_part_number)

    def set_obj(self, db_obj: PartNumberMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`PartNumberMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.SetValue('')
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.part_number)
            self.setEnabled(True)

    def _on_part_number(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the part number event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        part_number = evt.GetValue()
        self.db_obj.part_number = part_number
