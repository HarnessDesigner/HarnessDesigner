# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from .base import BaseMixin, DefaultStoredValue, DefaultStoredValueType

from ....ui import prop_ctrls as _prop_ctrls


class WeightMixin(BaseMixin):
    """Represent a weight mixin in :mod:`harness_designer.database.global_db.mixins.weight`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    _stored_weight: float | DefaultStoredValueType = DefaultStoredValue

    @property
    def weight(self) -> float:
        """Return the weight.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: float
        """
        if self._stored_weight is DefaultStoredValue:
            self._stored_weight = self._table.select('weight', id=self._db_id)[0][0]

        return self._stored_weight

    @weight.setter
    def weight(self, value: float):
        """Set the weight.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: float
        """
        self._stored_weight = value
        self._table.update(self._db_id, weight=value)
        self._populate('weight')


class WeightControl(_prop_ctrls.FloatProperty):
    """Represent a weight control in :mod:`harness_designer.database.global_db.mixins.weight`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`WeightControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        self.db_obj: WeightMixin = None

        super().__init__(parent, 'Weight', min_value=0.01, max_value=999.99, increment=0.01, units='g')

        self.propertyChanged.connect(self._on_weight)

    def set_obj(self, db_obj: WeightMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`WeightMixin`
        """
        self.db_obj = db_obj
        if db_obj is None:
            self.SetValue(0.0)
            self.setEnabled(False)
        else:
            self.SetValue(db_obj.weight)
            self.setEnabled(True)

    def _on_weight(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the weight event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        weight = evt.GetValue()
        self.db_obj.weight = weight
