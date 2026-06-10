# © 2025-2026 Kevin G. Schlosser <kevin.g.schlosser@gmail.com>

from typing import TYPE_CHECKING

from ....ui import prop_ctrls as _prop_ctrls
from .base import BaseMixin


if TYPE_CHECKING:
    from .. import temperature as _temperature  # NOQA


class TemperatureMixin(BaseMixin):
    """Represent a temperature mixin in :mod:`harness_designer.database.global_db.mixins.temperature`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    @property
    def min_temp(self) -> "_temperature.Temperature":
        """Return the min temp.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_temperature.Temperature`
        """
        from .. import temperature as _temperature  # NOQA

        min_temp_id = self._table.select('min_temp_id', id=self._db_id)
        return _temperature.Temperature(self._table.db.temperatures_table, min_temp_id[0][0])

    @property
    def min_temp_id(self) -> int:
        """Return the min temp ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('min_temp_id', id=self._db_id)[0][0]

    @min_temp_id.setter
    def min_temp_id(self, value: int):
        """Set the min temp ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, min_temp_id=value)
        self._populate('min_temp_id')

    @property
    def max_temp(self) -> "_temperature.Temperature":
        """Return the max temp.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: :class:`_temperature.Temperature`
        """
        from .. import temperature as _temperature  # NOQA

        max_temp_id = self._table.select('max_temp_id', id=self._db_id)
        return _temperature.Temperature(self._table.db.temperatures_table, max_temp_id[0][0])

    @property
    def max_temp_id(self) -> int:
        """Return the max temp ID.

        UNKNOWN details are inferred from the callable name and signature.

        :returns: Property value. UNKNOWN details.
        :rtype: int
        """
        return self._table.select('max_temp_id', id=self._db_id)[0][0]

    @max_temp_id.setter
    def max_temp_id(self, value: int):
        """Set the max temp ID.

        UNKNOWN details are inferred from the callable name and signature.

        :param value: Value to store or process.
        :type value: int
        """
        self._table.update(self._db_id, max_temp_id=value)
        self._populate('max_temp_id')


class TemperatureControl(_prop_ctrls.Category):
    """Represent a temperature control in :mod:`harness_designer.database.global_db.mixins.temperature`.

    UNKNOWN details are inferred from the class name and surrounding code.
    """

    def __init__(self, parent):
        """Initialise the :class:`TemperatureControl` instance.

        UNKNOWN details are inferred from the callable name and signature.

        :param parent: Parent object.
        :type parent: UNKNOWN
        """
        super().__init__(parent, 'Temperatures')

        self.choices: list[str] = []
        self.db_obj: TemperatureMixin = None

        self.min_temp_ctrl = _prop_ctrls.ComboBoxProperty(self, 'Minimum')
        self.max_temp_ctrl = _prop_ctrls.ComboBoxProperty(self, 'Maximum')

        self.addWidget(self.min_temp_ctrl)
        self.addWidget(self.max_temp_ctrl)

        self.min_temp_ctrl.propertyChanged.connect(self._on_min_temp)
        self.max_temp_ctrl.propertyChanged.connect(self._on_max_temp)

    def set_obj(self, db_obj: TemperatureMixin):
        """Set the obj.

        UNKNOWN details are inferred from the callable name and signature.

        :param db_obj: Database-backed object.
        :type db_obj: :class:`TemperatureMixin`
        """
        self.db_obj = db_obj

        if db_obj is None:
            self.choices = []

            self.min_temp_ctrl.SetItems(self.choices)
            self.min_temp_ctrl.SetValue('')
            self.max_temp_ctrl.SetItems(self.choices)
            self.max_temp_ctrl.SetValue('')
            self.min_temp_ctrl.setEnabled(False)
            self.max_temp_ctrl.setEnabled(False)
        else:
            min_temp = db_obj.min_temp
            max_temp = db_obj.max_temp

            db_obj.table.execute(f'SELECT name FROM temperatures;')
            rows = db_obj.table.fetchall()
            self.choices = sorted([row[0] for row in rows])

            self.min_temp_ctrl.SetItems(self.choices)
            self.min_temp_ctrl.SetValue(min_temp.name)
            self.max_temp_ctrl.SetItems(self.choices)
            self.max_temp_ctrl.SetValue(max_temp.name)

            self.min_temp_ctrl.setEnabled(True)
            self.max_temp_ctrl.setEnabled(True)

    def _on_min_temp(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the min temp event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM temperatures WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.temperatures_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.min_temp_ctrl.SetItems(self.choices)
            self.min_temp_ctrl.SetValue(name)

            value = self.max_temp_ctrl.GetValue()
            self.max_temp_ctrl.SetItems(self.choices)
            self.max_temp_ctrl.SetValue(value)

        self.db_obj.min_temp_id = db_id

    def _on_max_temp(self, evt: _prop_ctrls.PropertyEvent):
        """Handle the max temp event.

        UNKNOWN details are inferred from the callable name and signature.

        :param evt: Event object.
        :type evt: :class:`_prop_ctrls.PropertyEvent`
        """
        name = evt.GetValue()

        self.db_obj.table.execute(f'SELECT id FROM temperatures WHERE name="{name}";')
        rows = self.db_obj.table.fetchall()

        if rows:
            db_id, desc = rows[0]
        else:
            db_obj = self.db_obj.table.db.temperatures_table.insert(name)
            db_id = db_obj.db_id

            self.choices.append(name)
            self.choices.sort()

            self.max_temp_ctrl.SetItems(self.choices)
            self.max_temp_ctrl.SetValue(name)

            value = self.min_temp_ctrl.GetValue()
            self.min_temp_ctrl.SetItems(self.choices)
            self.min_temp_ctrl.SetValue(value)

        self.db_obj.max_temp_id = db_id
